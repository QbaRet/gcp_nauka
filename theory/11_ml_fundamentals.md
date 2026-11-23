Many PMLE questions are not about Google Cloud at all — they test whether you can read a metric, spot
leakage, handle imbalanced classes or pick a model type. This is the biggest group of questions in the
bank, so it pays to have these reflexes.

## Classification metrics

Confusion matrix: **TP**, **FP** (false alarm), **FN** (miss), **TN**.

| Metric | Formula | Optimise when… |
|---|---|---|
| **Precision** | TP / (TP + FP) | False positives are expensive (spam filter deleting real mail, flagging innocent customers) |
| **Recall** (sensitivity, TPR) | TP / (TP + FN) | False negatives are expensive (fraud, cancer screening, safety defects) |
| **F1** | Harmonic mean of precision & recall | Need a balance; imbalanced data |
| **Accuracy** | (TP + TN) / all | Only with balanced classes — misleading with imbalance |
| **ROC AUC** | Area under TPR vs FPR curve | Threshold-independent ranking quality; balanced-ish data |
| **PR AUC** (average precision) | Area under precision–recall curve | **Imbalanced data** where positives matter (fraud, rare disease) |
| **Log loss** | Penalises confident wrong probabilities | Calibrated probabilities matter |

**Threshold**: classifiers output scores; moving the threshold trades precision for recall. If the
business says "we must catch 95 % of fraud", choose the threshold on the PR curve that gives recall ≥ 0.95
and accept the precision. You don't need to retrain to change the trade-off.

## Regression and other metrics

| Metric | Notes |
|---|---|
| **MAE** | Average absolute error; robust to outliers; same unit as target |
| **RMSE** | Penalises large errors more; sensitive to outliers |
| **MAPE** | Percentage error; breaks near zero values |
| **R²** | Share of variance explained |
| Ranking/recommendation | Precision@k, recall@k, NDCG, MAP |
| Forecasting | MAE/RMSE/MAPE/WAPE on a **future** holdout |
| Generation | BLEU/ROUGE (with references), rubric-based LLM-as-a-judge |

Always compare against a **baseline** (majority class, last value, simple heuristic, linear model).

## Imbalanced data

- Use the right metric (PR AUC, recall at precision X, F1) — never accuracy alone.
- **Class weights** (e.g. BQML `AUTO_CLASS_WEIGHTS`, Keras `class_weight`), **downsampling the majority
  with up-weighting**, or **oversampling** the minority (SMOTE-style) — on the **training split only**.
- Stratified splits so validation contains positives.
- Collect more positive examples if possible; anomaly detection approaches when positives are extremely
  rare.

## Overfitting vs underfitting

| | Training error | Validation error | Fixes |
|---|---|---|---|
| **Underfitting** (high bias) | High | High | Bigger model, more features, train longer, less regularisation |
| **Overfitting** (high variance) | Low | High (gap grows) | More data, augmentation, **regularisation** (L1/L2, dropout), **early stopping**, simpler model, fewer features |

- **L1** pushes weights to zero → feature selection, sparse models. **L2** shrinks weights smoothly.
- **Dropout** randomly disables units in neural nets. **Early stopping** halts when validation loss rises.
- Data augmentation (images: flips, crops, colour) increases effective data.

## Data leakage and splits

- Leakage = training uses information not available at prediction time (future data, target proxies,
  statistics computed on the whole dataset, duplicates across splits).
- Split **before** preprocessing; fit scalers/vocabularies on training data.
- Time series → chronological split. Users/patients/devices → group split. Duplicates/near-duplicates →
  deduplicate before splitting.
- Train / validation (tuning) / test (final, touched once).
- Cross-validation for small datasets.

## Choosing the model type

| Problem | Typical choices |
|---|---|
| Tabular classification/regression | Gradient-boosted trees (XGBoost, BQML boosted trees), AutoML tabular; linear/logistic for interpretability |
| Images | CNNs / vision transformers, transfer learning; AutoML image |
| Text | Foundation models (Gemini) / transformers, embeddings + classifier |
| Time series forecasting | ARIMA_PLUS (BQML), AutoML forecasting, TimesFM, DNN/sequence models |
| Recommendations | Matrix factorization, two-tower retrieval + ranking models |
| Anomaly detection | Autoencoders, k-means distance, isolation forest, ARIMA residuals |
| Segmentation (no labels) | k-means / clustering |
| Interpretability required | Linear/logistic, small trees, GAMs + feature attributions |

**Transfer learning**: start from a pre-trained model and fine-tune — the default for images/text with
limited labelled data.

## Training dynamics

- **Learning rate** too high → loss oscillates or NaN; too low → slow progress. Use schedules/warm-up.
- Larger batch → faster per epoch, may need higher LR; very large batches can generalise worse.
- Vanishing/exploding gradients → normalisation (batch/layer norm), residual connections, gradient
  clipping, ReLU-family activations.

## ⚖️ Which metric for which business goal

| Business statement | Metric to optimise |
|---|---|
| "Don't miss any fraudulent transaction" | Recall (at acceptable precision) |
| "Only alert the team when we're sure" | Precision |
| "Rare positives, compare models overall" | PR AUC |
| "Rank customers by risk" | ROC AUC |
| "Probabilities feed a pricing formula" | Log loss / calibration |
| "Forecast error in units, robust to outliers" | MAE |
| "Big errors are very costly" | RMSE |

## ⚖️ Overfitting fix menu

| Situation | Best fix |
|---|---|
| Lots of features, little data | L1 regularisation / feature selection |
| Deep net memorises training set | Dropout, L2, early stopping, augmentation |
| Validation loss starts rising mid-training | Early stopping (restore best checkpoint) |
| Model too simple, both errors high | Increase capacity — it's underfitting |

## 🪤 Exam traps

- **99 % accuracy on 1 % positive class** = useless model; look at recall/precision/PR AUC.
- **Oversampling before splitting** → duplicates in validation → leakage.
- **Retraining to change precision/recall** — just move the threshold.
- **Treating overfitting with a bigger model** (or underfitting with more regularisation).
- **Evaluating forecasts with random splits.**

## ✅ Key takeaways

- Precision when false positives hurt, recall when misses hurt; PR AUC for imbalance.
- Overfitting → regularise, more data, early stopping; underfitting → more capacity.
- Split first, then preprocess; split by time/group when rows are related.
- Boosted trees for tabular, transfer learning for images/text, ARIMA/AutoML for forecasting.
