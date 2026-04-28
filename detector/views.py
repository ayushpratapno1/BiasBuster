import base64
import io
import json
import zlib

import pandas as pd
from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST

SENSITIVE_KEYWORDS = [
    'gender', 'sex', 'age', 'race', 'caste', 'religion',
    'ethnicity', 'nationality', 'disability', 'marital',
    'color', 'orientation', 'income',
]

SAMPLE_THRESHOLD = 5000


def _compress_data(json_str):
    """Compress a JSON string for safe transport in a hidden form field."""
    return base64.urlsafe_b64encode(zlib.compress(json_str.encode())).decode()


def _decompress_data(payload):
    """Reverse of _compress_data."""
    return zlib.decompress(base64.urlsafe_b64decode(payload)).decode()


def _detect_sensitive(columns):
    """Return column names that match known sensitive-attribute keywords."""
    found = []
    for col in columns:
        name = col.lower().replace('_', ' ').replace('-', ' ')
        if any(kw in name for kw in SENSITIVE_KEYWORDS):
            found.append(col)
    return found


def _build_summary(df):
    """Produce a serialisable dict describing the dataset's structure."""
    cols = []
    for c in df.columns:
        cols.append({
            'name': c,
            'dtype': 'Categorical' if df[c].dtype == 'object' else 'Numerical',
            'missing': int(df[c].isnull().sum()),
            'unique': int(df[c].nunique()),
        })
    return {
        'total_rows': int(len(df)),
        'total_cols': int(len(df.columns)),
        'total_missing': int(df.isnull().sum().sum()),
        'columns': cols,
    }


def _generate_insights(result_dict, sensitive, target, bias_detected):
    """Build human-readable insight strings from the group analysis."""
    groups = list(result_dict.keys())
    vals = list(result_dict.values())
    mx_i, mn_i = vals.index(max(vals)), vals.index(min(vals))
    mx_g, mx_v = groups[mx_i], vals[mx_i]
    mn_g, mn_v = groups[mn_i], vals[mn_i]

    out = []
    if bias_detected:
        out.append(
            f"The average {target} for {mx_g} ({round(mx_v, 4)}) is significantly "
            f"higher than {mn_g} ({round(mn_v, 4)}), indicating potential bias."
        )
        out.append(
            f"The disparity between the highest and lowest groups is "
            f"{round(abs(mx_v - mn_v), 4)}."
        )
        if mx_v:
            out.append(
                f"The disadvantaged group ({mn_g}) achieves only "
                f"{round(mn_v / mx_v * 100, 1)}% of the advantaged "
                f"group's ({mx_g}) outcome."
            )
    else:
        out.append(
            f"Outcomes are well-balanced across {sensitive} groups, ranging "
            f"from {round(mn_v, 4)} to {round(mx_v, 4)}."
        )
        out.append(
            f"Inter-group disparity is only {round(abs(mx_v - mn_v), 4)}, "
            f"within the acceptable threshold (< 0.1)."
        )
    return out


# ─── Main page ────────────────────────────────────────────────

def index(request):
    if request.method == 'POST':

        # STEP 1: Upload CSV
        if request.FILES.get('dataset'):
            file = request.FILES['dataset']

            if file.size > 5 * 1024 * 1024:
                return render(request, 'index.html', {
                    'error': 'File exceeds the 5 MB limit. Please upload a smaller file.'
                })

            try:
                df = pd.read_csv(file)
            except Exception:
                return render(request, 'index.html', {
                    'error': 'Could not parse the file. Please ensure it is a valid CSV.'
                })

            sampled = False
            original_rows = int(len(df))
            if len(df) > SAMPLE_THRESHOLD:
                df = df.sample(n=SAMPLE_THRESHOLD, random_state=42)
                sampled = True

            columns = df.columns.tolist()
            summary = _build_summary(df)
            suggested = _detect_sensitive(columns)

            return render(request, 'index.html', {
                'columns': columns,
                'summary': summary,
                'summary_json': json.dumps(summary),
                'suggested_sensitive': suggested,
                'sampled': sampled,
                'original_rows': original_rows,
                'sample_size': SAMPLE_THRESHOLD,
                'dataset_json': _compress_data(df.to_json()),
            })

        # STEP 2: Analyse
        elif request.POST.get('process'):
            payload = request.POST.get('dataset_json')
            if not payload:
                return render(request, 'index.html', {
                    'error': 'Dataset missing. Please upload your CSV again.'
                })

            sensitive = request.POST.get('sensitive')
            target = request.POST.get('target')

            try:
                df = pd.read_json(io.StringIO(_decompress_data(payload)))
            except Exception:
                return render(request, 'index.html', {
                    'error': 'Dataset could not be loaded. Please re-upload your CSV.'
                })

            if sensitive not in df.columns or target not in df.columns:
                return render(request, 'index.html', {
                    'error': 'Selected columns not found in the dataset. Please re-upload.'
                })

            result = df.groupby(sensitive)[target].mean()
            result_dict = result.to_dict()
            vals = list(result_dict.values())
            mx, mn = max(vals), min(vals)

            fairness_score = round((mn / mx) * 100, 2) if mx else 0
            bias_detected = abs(mx - mn) > 0.1

            insights = _generate_insights(
                result_dict, sensitive, target, bias_detected
            )

            if bias_detected:
                suggestions = [
                    "Rebalance your dataset using oversampling or undersampling techniques",
                    "Remove or reduce the sensitive attribute's influence during model training",
                    "Apply fairness-aware algorithms such as adversarial debiasing or reweighing",
                    "Audit your data collection pipeline for systemic biases",
                ]
            else:
                suggestions = [
                    "Dataset appears balanced — keep monitoring as new data arrives",
                    "Run periodic bias audits to maintain fairness over time",
                ]

            sim_mean = round(float(df[target].mean()), 4)
            sim_std = round(float(df[target].std()), 4)
            sim_message = (
                f'Without grouping by "{sensitive}", the overall {target} mean '
                f'is {sim_mean} (std: {sim_std}). Inter-group disparity is '
                f'eliminated, yielding a fairness score of 100%.'
            )

            summary = _build_summary(df)

            return render(request, 'result.html', {
                'sensitive': sensitive,
                'target': target,
                'result': result_dict,
                'result_json': json.dumps(result_dict),
                'fairness_score': fairness_score,
                'bias_detected': bias_detected,
                'suggestions': suggestions,
                'insights': insights,
                'insights_json': json.dumps(insights),
                'suggestions_json': json.dumps(suggestions),
                'summary': summary,
                'summary_json': json.dumps(summary),
                'sim_original_score': fairness_score,
                'sim_mean': sim_mean,
                'sim_std': sim_std,
                'sim_message': sim_message,
            })

    return render(request, 'index.html')


# ─── AJAX: Bias simulation ───────────────────────────────────

@require_POST
def simulate(request):
    try:
        body = json.loads(request.body)
        sensitive, target = body['sensitive'], body['target']
        dataset_payload = body.get('dataset_json', '')

        if not dataset_payload:
            return JsonResponse({'error': 'No dataset provided.'}, status=400)

        df = pd.read_json(io.StringIO(_decompress_data(dataset_payload)))

        orig = df.groupby(sensitive)[target].mean().to_dict()
        orig_vals = list(orig.values())
        orig_mx, orig_mn = max(orig_vals), min(orig_vals)
        orig_score = round((orig_mn / orig_mx) * 100, 2) if orig_mx else 0

        sim_mean = round(float(df[target].mean()), 4)
        sim_std = round(float(df[target].std()), 4)

        return JsonResponse({
            'original_score': orig_score,
            'simulated_score': 100.0,
            'simulated_mean': sim_mean,
            'simulated_std': sim_std,
            'message': (
                f'Without grouping by "{sensitive}", the overall {target} mean '
                f'is {sim_mean} (std: {sim_std}). Inter-group disparity is '
                f'eliminated, yielding a fairness score of 100%.'
            ),
        })
    except Exception:
        return JsonResponse({'error': 'Simulation failed.'}, status=400)


# ─── AJAX: Download report ───────────────────────────────────

@require_POST
def download_report(request):
    body = json.loads(request.body)

    lines = [
        '=' * 60,
        '   BIABUSTERS — Bias Analysis Report',
        '   Generated by Team Fairlytics',
        '=' * 60,
        '',
        f"  Sensitive Column :  {body.get('sensitive', 'N/A')}",
        f"  Target Column    :  {body.get('target', 'N/A')}",
        f"  Fairness Score   :  {body.get('fairness_score', 'N/A')}%",
        f"  Bias Detected    :  {'Yes' if body.get('bias_detected') else 'No'}",
        '',
        '-' * 60,
        '  GROUP OUTCOME RATES',
        '-' * 60,
    ]
    for grp, val in body.get('result', {}).items():
        lines.append(f'    {str(grp):30s} {val}')

    lines += ['', '-' * 60, '  INSIGHTS', '-' * 60]
    for i, t in enumerate(body.get('insights', []), 1):
        lines.append(f'    {i}. {t}')

    lines += ['', '-' * 60, '  RECOMMENDATIONS', '-' * 60]
    for i, t in enumerate(body.get('suggestions', []), 1):
        lines.append(f'    {i}. {t}')

    lines += ['', '=' * 60, '  End of Report', '=' * 60]

    resp = HttpResponse('\n'.join(lines), content_type='text/plain')
    resp['Content-Disposition'] = 'attachment; filename="biasbuster_report.txt"'
    return resp
