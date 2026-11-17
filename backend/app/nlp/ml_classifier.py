"""
Machine Learning Intent Classifier Baseline.
Uses Scikit-Learn TF-IDF Vectorizer (word and char n-grams) + Logistic Regression.
Provides offline statistical classification alongside Rule-Based and Gemini approaches.
"""
import os
from pathlib import Path
import joblib
import numpy as np
from typing import Dict, List, Tuple, Optional
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.metrics import accuracy_score, precision_recall_fscore_support, classification_report


# Extensive training corpus spanning all supported groundwater query intents
TRAINING_DATA: List[Tuple[str, str]] = [
    # 1. get_assessment_years
    ("What assessment years are available in the database?", "get_assessment_years"),
    ("Which years of groundwater data are available?", "get_assessment_years"),
    ("Show available assessment periods", "get_assessment_years"),
    ("List all assessment years", "get_assessment_years"),
    ("What years can I query?", "get_assessment_years"),
    ("Can I check groundwater data for 2026?", "get_assessment_years"),
    ("Is 2020 and 2023 data available in the system?", "get_assessment_years"),
    ("Which assessment years are present in IN-GRES dataset?", "get_assessment_years"),

    # 2. get_state_list
    ("Which states have groundwater data?", "get_state_list"),
    ("Show all states and union territories", "get_state_list"),
    ("List available states in India", "get_state_list"),
    ("What states are covered in the database?", "get_state_list"),
    ("Give me the list of states with groundwater assessment", "get_state_list"),
    ("Show all states covered", "get_state_list"),

    # 3. get_country_summary
    ("Show national groundwater statistics for 2022", "get_country_summary"),
    ("What is the all-India groundwater recharge?", "get_country_summary"),
    ("Show country-wide groundwater summary", "get_country_summary"),
    ("National groundwater extraction total in India", "get_country_summary"),
    ("All India total extractable groundwater resource", "get_country_summary"),
    ("Across India national groundwater status", "get_country_summary"),

    # 4. get_state_summary
    ("Show groundwater statistics for Bihar", "get_state_summary"),
    ("Give me the groundwater overview for Punjab in 2022", "get_state_summary"),
    ("What is the state-level groundwater situation in Rajasthan?", "get_state_summary"),
    ("Summary of groundwater in Uttar Pradesh", "get_state_summary"),
    ("State summary for Maharashtra", "get_state_summary"),
    ("Overall groundwater status of Haryana", "get_state_summary"),

    # 5. get_district_summary
    ("Show groundwater data for Patna district in Bihar", "get_district_summary"),
    ("Complete groundwater situation in Gaya", "get_district_summary"),
    ("Full groundwater profile for Jalandhar Punjab", "get_district_summary"),
    ("All groundwater statistics for Lucknow", "get_district_summary"),
    ("Groundwater report for Jaipur district", "get_district_summary"),
    ("District profile for Amritsar in 2022", "get_district_summary"),

    # 6. get_groundwater_recharge
    ("What is the groundwater recharge in Patna district?", "get_groundwater_recharge"),
    ("Show annual groundwater recharge in Bihar for 2022", "get_groundwater_recharge"),
    ("How much recharge occurs in Gaya in monsoon season?", "get_groundwater_recharge"),
    ("Total annual recharge in Jalandhar Punjab", "get_groundwater_recharge"),
    ("Recharge figures for Jaipur district", "get_groundwater_recharge"),
    ("What is the total recharge in Ludhiana in 2020?", "get_groundwater_recharge"),
    ("Calculate groundwater recharge in Lucknow", "get_groundwater_recharge"),

    # 7. get_extractable_groundwater
    ("What is the extractable groundwater in Patna?", "get_extractable_groundwater"),
    ("Show annual extractable groundwater resources in Bihar", "get_extractable_groundwater"),
    ("Extractable resource in Gaya district 2022", "get_extractable_groundwater"),
    ("How much extractable water is available in Punjab?", "get_extractable_groundwater"),
    ("Future availability of groundwater in Jalandhar", "get_extractable_groundwater"),
    ("Net extractable groundwater resource for Jaipur", "get_extractable_groundwater"),

    # 8. get_groundwater_extraction
    ("What is the groundwater extraction in Patna district in 2022?", "get_groundwater_extraction"),
    ("How much groundwater is extracted in Bihar?", "get_groundwater_extraction"),
    ("Groundwater extraction for irrigation in Gaya", "get_groundwater_extraction"),
    ("Total annual groundwater extraction in Jalandhar Punjab", "get_groundwater_extraction"),
    ("Annual extraction volume in Jaipur in 2026", "get_groundwater_extraction"),
    ("How much groundwater is pumped in Amritsar?", "get_groundwater_extraction"),
    ("Extraction of groundwater in Ludhiana district", "get_groundwater_extraction"),

    # 9. get_stage_of_extraction
    ("What is the stage of groundwater extraction in Gaya?", "get_stage_of_extraction"),
    ("Show stage of extraction percentage in Patna", "get_stage_of_extraction"),
    ("What percent of groundwater is extracted in Jalandhar?", "get_stage_of_extraction"),
    ("Stage of groundwater development in Punjab", "get_stage_of_extraction"),
    ("Is the stage of extraction above 100% in Jaipur?", "get_stage_of_extraction"),
    ("Stage of extraction for Amritsar district in 2023", "get_stage_of_extraction"),

    # 10. get_assessment_category
    ("Which assessment category does Gaya belong to?", "get_assessment_category"),
    ("Is Patna safe or critical in groundwater?", "get_assessment_category"),
    ("Classification of Jalandhar district groundwater category", "get_assessment_category"),
    ("What category is Ludhiana district classified under?", "get_assessment_category"),
    ("Is Jaipur safe semi-critical or over-exploited?", "get_assessment_category"),
    ("Groundwater category of Lucknow district", "get_assessment_category"),

    # 11. get_overexploited_units
    ("Which districts in Bihar are over-exploited?", "get_overexploited_units"),
    ("List all over-exploited districts in Punjab", "get_overexploited_units"),
    ("Are there any overexploited assessment units in Rajasthan?", "get_overexploited_units"),
    ("Show over-exploited blocks in Haryana in 2022", "get_overexploited_units"),
    ("Overexploited units in Uttar Pradesh", "get_overexploited_units"),
    ("Which regions are overexploited in Gujarat?", "get_overexploited_units"),

    # 12. compare_locations
    ("Compare groundwater extraction between Patna and Gaya", "compare_locations"),
    ("Compare recharge in Jalandhar versus Amritsar", "compare_locations"),
    ("Patna vs Gaya stage of extraction comparison", "compare_locations"),
    ("Compare extraction in Ludhiana and Bathinda", "compare_locations"),
    ("Comparison between Jaipur and Jodhpur groundwater", "compare_locations"),
    ("Compare Lucknow vs Varanasi extractable resources", "compare_locations"),

    # 13. compare_assessment_years
    ("Compare groundwater extraction in Patna between 2020 and 2026", "compare_assessment_years"),
    ("Compare 2020 and 2022 recharge in Bihar", "compare_assessment_years"),
    ("Comparison of extraction between 2022 and 2023 for Jalandhar", "compare_assessment_years"),
    ("Compare both years for Patna", "compare_assessment_years"),
    ("How did groundwater change from 2020 to 2026 in Gaya?", "compare_assessment_years"),
    ("Difference in extraction between 2022 and 2025 in Punjab", "compare_assessment_years"),

    # 14. get_districts_in_state
    ("List all districts in Bihar that have data", "get_districts_in_state"),
    ("Which districts in Punjab are covered?", "get_districts_in_state"),
    ("Show all districts with groundwater assessment in Rajasthan", "get_districts_in_state"),
    ("What districts exist for Uttar Pradesh?", "get_districts_in_state"),

    # 15. get_historical_groundwater_data
    ("Show historical groundwater extraction in Patna", "get_historical_groundwater_data"),
    ("Historical trend of recharge in Bihar across all years", "get_historical_groundwater_data"),
    ("Show multi-year groundwater trend for Jalandhar", "get_historical_groundwater_data"),
    ("Year-over-year groundwater extraction trend in Punjab", "get_historical_groundwater_data"),
    ("Time series data of groundwater in Gaya from 2020 to 2026", "get_historical_groundwater_data"),

    # 16. get_groundwater_level
    ("What is the groundwater level in Patna?", "get_groundwater_level"),
    ("Depth to water table in Gaya well", "get_groundwater_level"),
    ("What is the well depth in Jalandhar?", "get_groundwater_level"),
    ("Show depth to water measurements in Rajasthan", "get_groundwater_level"),

    # 17. domain_explanation
    ("What is an aquifer?", "domain_explanation"),
    ("Explain what over-exploited means", "domain_explanation"),
    ("What is groundwater depletion?", "domain_explanation"),
    ("Explain the difference between recharge and extraction", "domain_explanation"),
    ("What does stage of groundwater extraction mean?", "domain_explanation"),
    ("What is IN-GRES portal?", "domain_explanation"),

    # 18. general_greeting
    ("Hello", "general_greeting"),
    ("Hi there", "general_greeting"),
    ("Good morning", "general_greeting"),
    ("Hey assistant", "general_greeting"),
]


class MLIntentClassifier:
    """Scikit-Learn TF-IDF + Logistic Regression Intent Classifier."""

    def __init__(self, model_path: Optional[str] = None):
        if model_path:
            self.model_path = model_path
        else:
            repo_root = Path(__file__).resolve().parents[3]
            candidate = repo_root / "data" / "ml_intent_model.joblib"
            if candidate.exists():
                self.model_path = str(candidate)
            else:
                self.model_path = os.path.join(
                    os.path.dirname(__file__), "..", "..", "data", "ml_intent_model.joblib"
                )
        self.pipeline: Optional[Pipeline] = None
        self._initialize_or_load()

    def _initialize_or_load(self):
        """Load persisted model or train a fresh pipeline."""
        if os.path.exists(self.model_path):
            try:
                self.pipeline = joblib.load(self.model_path)
                return
            except Exception:
                pass
        self.train_and_save()

    def train_and_save(self) -> Dict[str, float]:
        """Train TF-IDF + Logistic Regression pipeline on corpus and persist."""
        texts = [item[0] for item in TRAINING_DATA]
        labels = [item[1] for item in TRAINING_DATA]

        # TF-IDF Vectorizer with unigrams and bigrams
        vectorizer = TfidfVectorizer(
            ngram_range=(1, 2),
            sublinear_tf=True,
            lowercase=True,
            strip_accents="unicode",
        )

        classifier = LogisticRegression(
            C=3.0,
            max_iter=1000,
            class_weight="balanced",
            random_state=42,
        )

        self.pipeline = Pipeline([
            ("tfidf", vectorizer),
            ("clf", classifier),
        ])

        self.pipeline.fit(texts, labels)

        # Save model
        os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
        try:
            joblib.dump(self.pipeline, self.model_path)
        except Exception:
            pass

        # Evaluate on training data
        preds = self.pipeline.predict(texts)
        acc = accuracy_score(labels, preds)
        p, r, f1, _ = precision_recall_fscore_support(labels, preds, average="weighted", zero_division=0)

        return {
            "accuracy": round(float(acc), 4),
            "precision": round(float(p), 4),
            "recall": round(float(r), 4),
            "f1": round(float(f1), 4),
            "total_samples": len(texts),
        }

    def predict(self, question: str) -> Dict:
        """
        Predict intent using trained statistical model.
        Returns predicted intent, confidence score, and top probability classes.
        """
        if not self.pipeline:
            self.train_and_save()

        probs = self.pipeline.predict_proba([question])[0]
        classes = self.pipeline.classes_
        top_idx = np.argmax(probs)
        confidence = float(probs[top_idx])
        predicted_intent = str(classes[top_idx])

        # Top 3 intents
        top_3_indices = np.argsort(probs)[-3:][::-1]
        top_3 = [
            {"intent": str(classes[i]), "probability": round(float(probs[i]), 4)}
            for i in top_3_indices
        ]

        return {
            "intent": predicted_intent,
            "confidence": round(confidence, 4),
            "top_classes": top_3,
            "model": "TF-IDF + Logistic Regression",
        }


# Singleton instance
_ml_classifier_instance: Optional[MLIntentClassifier] = None


def get_ml_classifier() -> MLIntentClassifier:
    global _ml_classifier_instance
    if _ml_classifier_instance is None:
        _ml_classifier_instance = MLIntentClassifier()
    return _ml_classifier_instance

