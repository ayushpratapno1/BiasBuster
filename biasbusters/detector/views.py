import pandas as pd
from django.shortcuts import render
import json
import io

def index(request):
    columns = None

    if request.method == 'POST':

        # STEP 1: Upload & read CSV (NO saving)
        if request.FILES.get('dataset'):
            file = request.FILES['dataset']

            df = pd.read_csv(file)

            # Store data in session
            request.session['data'] = df.to_json()

            columns = df.columns.tolist()

            return render(request, 'index.html', {
                'columns': columns
            })

        # STEP 2: Analyze
        elif request.POST.get('process'):
            sensitive = request.POST.get('sensitive')
            target = request.POST.get('target')

            # Load from session
            df = pd.read_json(io.StringIO(request.session.get('data')))

            # 🔥 CORE LOGIC
            result = df.groupby(sensitive)[target].mean()

            result_dict = result.to_dict()

            values = list(result_dict.values())
            max_val = max(values)
            min_val = min(values)

            fairness_score = round((min_val / max_val) * 100, 2) if max_val != 0 else 0

            bias_detected = abs(max_val - min_val) > 0.1

            # Suggestions
            suggestions = []
            if bias_detected:
                suggestions.append("Rebalance dataset across groups")
                suggestions.append("Remove or reduce influence of sensitive attribute")
                suggestions.append("Use fairness-aware algorithms")
            else:
                suggestions.append("Dataset appears balanced")

            return render(request, 'result.html', {
                'sensitive': sensitive,
                'target': target,
                'result': result_dict,
                'result_json': json.dumps(result_dict),
                'fairness_score': fairness_score,
                'bias_detected': bias_detected,
                'suggestions': suggestions
            })

    return render(request, 'index.html')