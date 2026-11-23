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

## Metrics by example

1 000 transactions, 50 of them fraud. The model flags 80; 40 of those are real fraud.

| | Predicted fraud | Predicted OK |
|---|---|---|
| **Fraud (50)** | TP = 40 | FN = 10 |
| **OK (950)** | FP = 40 | TN = 910 |

- Precision = 40 / 80 = **0.50** — half the alerts are false.
- Recall = 40 / 50 = **0.80** — 20 % of fraud is missed.
- F1 = 2·0.5·0.8 / 1.3 ≈ **0.62**.
- Accuracy = (40 + 910) / 1000 = **0.95** — yet a model that flags *nothing* scores 0.95 too.
- FPR = 40 / 950 ≈ 0.04 (x-axis of the ROC curve).

## Calibration

A model is **calibrated** if, among predictions of 0.8, about 80 % are positive. Needed when
probabilities feed decisions (expected loss, pricing, bidding). Check with a reliability diagram /
log loss; fix with **Platt scaling** or **isotonic regression**. Down-sampling the majority class
distorts probabilities — re-weight or re-calibrate afterwards.

## Clustering and unsupervised evaluation

No labels → judge clusters with **silhouette score**, **Davies-Bouldin** (lower is better), the
**elbow** of within-cluster distance vs k — and, most importantly, whether segments are actionable for the
business. Scale features first for distance-based methods (k-means).

## Recommendation systems basics

| Approach | Idea | Weakness |
|---|---|---|
| **Content-based** | Recommend items similar to what the user liked (item features) | Narrow, needs item features |
| **Collaborative filtering** (matrix factorization) | Users who behaved alike like alike items | **Cold start** for new users/items |
| **Hybrid / two-tower** | Learn user and item embeddings from features + interactions; retrieve candidates, then **rank** | More complex |

Cold start fixes: popularity/trending, content features, asking for preferences at onboarding.
**Implicit feedback** (clicks, watch time) is plentiful but noisy; **explicit** (ratings) is sparse.

## Cross-validation and the test set

k-fold cross-validation gives a more stable estimate on small data; use **time-series CV** (expanding
window) for temporal data. Keep a final **test set untouched** until the end — every decision made using
it (tuning, feature selection) leaks optimism into the reported score.

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

## 🧪 Worked scenarios

### 1. 99.9 % accuracy
A fraud model reports 99.9 % accuracy on data with 0.1 % fraud. Is it good?

**Answer:** Unknown — predicting "never fraud" achieves the same. Report **recall, precision, PR AUC**
and the confusion matrix.

### 2. Validation loss rises after epoch 8
Training loss keeps falling, validation loss starts rising at epoch 8.

**Answer:** **Overfitting** — **early stopping** with best-checkpoint restore; then regularisation /
augmentation / more data.

### 3. New users get bad recommendations
A matrix-factorization recommender works well for active users but poorly for new sign-ups.

**Answer:** **Cold start** — fall back to popularity or content-based features, or use a hybrid /
two-tower model with user features.

### 4. Probabilities drive pricing
Predicted default probabilities are multiplied by loan value to price risk; a model with high AUC
gives systematically too-high probabilities.

**Answer:** AUC measures ranking, not calibration. **Calibrate** (Platt / isotonic) and monitor **log
loss**.

### 5. "Catch 90 % of defects"
Quality control wants to catch at least 90 % of defective parts.

**Answer:** Choose the **threshold** that gives **recall ≥ 0.9** on validation data and report the
resulting precision — no retraining needed.

## 🪤 Exam traps

- **99 % accuracy on 1 % positive class** = useless model; look at recall/precision/PR AUC.
- **Oversampling before splitting** → duplicates in validation → leakage.
- **Retraining to change precision/recall** — just move the threshold.
- **Treating overfitting with a bigger model** (or underfitting with more regularisation).
- **Evaluating forecasts with random splits.**
- **AUC as proof of good probabilities** — ranking quality ≠ calibration.
- **Tuning on the test set** — the final score becomes over-optimistic; use a validation set or CV.

## ✅ Key takeaways

- Precision when false positives hurt, recall when misses hurt; PR AUC for imbalance.
- Overfitting → regularise, more data, early stopping; underfitting → more capacity.
- Split first, then preprocess; split by time/group when rows are related.
- Boosted trees for tabular, transfer learning for images/text, ARIMA/AutoML for forecasting.
