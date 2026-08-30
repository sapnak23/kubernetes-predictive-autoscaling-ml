# Machine Learning-Based Predictive Autoscaling in Kubernetes Cloud Environments

This repository contains the experimental artefacts, datasets, scripts, and evaluation outputs produced for an MSc research project investigating machine learning-based CPU forecasting for prediction-informed Kubernetes autoscaling.

The experiments were conducted using an application deployed on Microsoft Azure Kubernetes Service (AKS). Workloads were generated using k6, Kubernetes Horizontal Pod Autoscaler (HPA) behaviour was monitored, and CPU and replica metrics were collected for subsequent machine learning analysis.

## Project Scope

The study investigates whether short-horizon CPU forecasting can provide useful information for Kubernetes resource-scaling decisions.

The work consists of three experimental stages:

- **Experiment 1:** Multiple controlled workload patterns used to investigate cross-workload CPU forecasting.
- **Experiment 2:** An intermediate long mixed-workload run used during development and calibration of the experimental pipeline.
- **Experiment 3:** A continuous mixed-workload experiment used for chronological CPU forecasting and post-hoc prediction-informed replica evaluation.

The machine learning models were evaluated offline. They did not directly replace or control the Kubernetes HPA during the experiments.

## Experimental Environment

The experimental pipeline used:

- Microsoft Azure Kubernetes Service (AKS)
- Kubernetes Horizontal Pod Autoscaler (HPA)
- k6 for workload generation
- Prometheus for metrics collection
- Grafana for monitoring and visualisation
- Python for data processing and machine learning
- scikit-learn for model development

The deployed test application was a Kubernetes `php-apache` workload.

## Repository Structure

```text
.
├── docs/
│   └── images/
├── experiment1/
│   ├── workloads/
│   ├── collection/
│   ├── data/
│   │   ├── raw/
│   │   ├── processed/
│   │   └── k6_summaries/
│   └── scripts/
├── experiment2/
├── experiment3/
│   ├── workload/
│   ├── collection/
│   ├── data/
│   │   ├── raw/
│   │   └── processed/
│   ├── modelling/
│   └── evaluation/
├── requirements.txt
└── README.md
```

## Experiment 1

Experiment 1 examined six workload patterns:

1. Baseline
2. Gradual ramp
3. Sudden spike
4. Oscillating load
5. Long mixed workload
6. Random bursty workload

The six raw datasets contained 1,562 observations. After cleaning, 1,332 observations remained, and time-based feature engineering produced 1,248 ML-ready observations.

Feature engineering was performed separately within each workload before the engineered datasets were combined. This prevented lag features and future targets from crossing workload boundaries.

The first four workloads were used for training, the long mixed workload for validation, and the random bursty workload for testing.

The models compared were:

- Persistence baseline
- Linear Regression
- Random Forest
- Gradient Boosting

On the unseen random-bursty workload, the persistence baseline achieved the best overall forecasting performance. This demonstrates the difficulty of generalising across substantially different workload patterns.

## Experiment 2

Experiment 2 was an intermediate mixed-workload experiment used during development and calibration.

A six-hour workload was prepared, but metric recording ended after approximately 2.5 hours. The resulting dataset is retained in the repository as an intermediate experimental artefact and was not used as the final evaluation experiment.

## Experiment 3

Experiment 3 used a longer mixed workload and a continuous temporal modelling approach.

The raw dataset contained 1,603 observations. A recording interruption was detected and represented using continuous segment identifiers so that historical lag features and future prediction targets were not constructed across the recording gap.

Feature engineering produced 1,585 ML-ready observations.

The dataset was divided chronologically:

- Training: 1,109 observations (70%)
- Validation: 238 observations (15%)
- Testing: 238 observations (15%)

No random shuffling was used.

The forecasting target was CPU utilisation approximately 30 seconds into the future.

### Forecasting Results

On the Experiment 3 test partition:

| Model | MAE | RMSE | R² |
|---|---:|---:|---:|
| Persistence Baseline | 6.895 | 11.937 | 0.698 |
| Linear Regression | 7.056 | 11.006 | 0.743 |
| Random Forest | 7.063 | 10.679 | 0.758 |
| Gradient Boosting | **6.655** | **10.196** | **0.780** |

Gradient Boosting achieved the best overall test performance and was therefore used for the subsequent prediction-informed replica evaluation.

## Prediction-Informed Replica Evaluation

The Experiment 3 forecasting results were used in a post-hoc comparison between:

- a reactive replica recommendation based on current CPU utilisation; and
- a prediction-informed recommendation based on forecast CPU approximately 30 seconds ahead.

Both use an HPA-style replica calculation bounded by the configured minimum and maximum replica limits.

The future CPU actually observed approximately 30 seconds later was used retrospectively to calculate a reference future replica requirement.

Key results on the 238 test observations were:

| Metric | Prediction-informed | Reactive |
|---|---:|---:|
| Mean absolute replica error | 0.555 | 0.567 |
| Exact replica recommendation | 58.0% | 64.7% |
| Within ±1 replica | 92.4% | 83.6% |
| Scale-up recommendations | 98 | 95 |

There were six test observations in which the prediction-informed method recommended an increase in replicas while the reactive method did not.

During CPU transitions greater than 10 percentage points, prediction-informed replica MAE was approximately 1.217 compared with 1.700 for the reactive method.

These results represent an offline recommendation comparison rather than measurements from a live ML-controlled autoscaler.

## Reproducing the Python Analysis

Install the required Python packages:

```bash
pip install -r requirements.txt
```

Experiment 1 processing and modelling scripts are located in:

```text
experiment1/scripts/
```

Experiment 3 feature engineering and model training are located in:

```text
experiment3/modelling/
```

The prediction-informed replica evaluation is located in:

```text
experiment3/evaluation/evaluate_predictive_scaling.py
```

The repository includes the processed datasets and generated result CSV files so that the reported outputs can also be inspected without retraining the models.

Generated `.joblib` model files are intentionally excluded from version control. They can be regenerated by running the training scripts.

## Experimental Evidence

Selected screenshots from the experimental environment are available in `docs/images/`, including evidence of:

- Azure AKS deployment
- k6 workload execution
- Kubernetes HPA behaviour
- Prometheus target health
- Grafana CPU monitoring
- Grafana replica monitoring

## Important Interpretation

This repository does **not** contain a production or live ML-driven Kubernetes autoscaling controller.

Machine learning was used to forecast future CPU utilisation. Prediction-informed replica recommendations were subsequently calculated and compared offline with reactive HPA-style recommendations.

Therefore, the results should be interpreted as evidence about the potential usefulness of short-horizon workload prediction for autoscaling decisions, rather than as a direct measurement of end-to-end performance from a deployed predictive autoscaler.

## Limitations

The study does not directly measure application latency, throughput, SLO attainment, cloud cost savings, or end-to-end benefits from deploying an ML controller.

The prediction-informed scaling comparison is a post-hoc evaluation based on recorded experimental data and does not reproduce every aspect of the Kubernetes HPA control loop.

## MSc Research Project

This repository accompanies an MSc research project in Advanced Computer Science (Cloud Computing) at the University of Leeds.
