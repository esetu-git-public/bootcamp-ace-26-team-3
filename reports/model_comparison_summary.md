# Model Training and Comparison Summary

## Best Model Selected: logreg
**Version**: v1.3.0-model-comparison
**Selection Criteria**: Highest ROC-AUC first, then F1-score, then recall (rejecting models with > 5% train/test accuracy gap).

### Metrics Summary Table

| Model Name | Train Accuracy | Test Accuracy | Train-Test Gap | Test ROC-AUC | Test F1-Score | Overfitted? |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| logreg | 0.8520 | 0.8536 | -0.0016 | 0.9463 | 0.7794 | No |
| rf | 1.0000 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | Yes |
| gb | 1.0000 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | Yes |
| xgboost | 1.0000 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | Yes |
| catboost | 1.0000 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | Yes |
