# MLflow tracking

Training creates `mlflow.db` for experiment metadata and an `artifacts/` directory for model files. The experiment is named `metro-traffic-capstone`; it records candidate estimator parameters and holdout metrics, then registers the selected proxy classifier and traffic regressor. Registry versions increase on subsequent runs rather than replacing earlier versions. `tracking_summary.json` is the portable, tracked export of actual run parameters, metrics, run IDs, and model-version numbers. The local database and artifact directory are ignored because their file URIs embed the machine-specific checkout path; regenerate them with the training command.

Start the local UI from the repository root, substituting the absolute checkout path:

```powershell
mlflow ui --backend-store-uri "sqlite:///C:/absolute/path/to/nus-capstone-final/part3_machine_learning/mlflow/mlflow.db"
```

The tracking store is local and is not a shared production registry. Use the README's repeatable training command to rebuild all experiments from the processed Part 2 input. Keep the data and model proxy-label caveats in view when interpreting any metric.
