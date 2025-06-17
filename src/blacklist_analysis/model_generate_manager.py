import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.metrics import (
    confusion_matrix, accuracy_score, precision_score,
    recall_score, f1_score, roc_auc_score
)

from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.svm import LinearSVC, SVC
from sklearn.neighbors import KNeighborsClassifier

class ModelAnalysisManager:
    def __init__(self, df, feature_cols, target_col, cat_features, num_features, test_size=0.2, random_state=42):
        self.df = df
        self.feature_cols = feature_cols
        self.target_col = target_col
        self.cat_features = cat_features
        self.num_features = num_features
        self.test_size = test_size
        self.random_state = random_state
        self.models = self._init_models()
        self.results = []

        self._prepare_data()

    def _init_models(self):
        return {
            "Logistic Regression": LogisticRegression(max_iter=1000),
            "Random Forest": RandomForestClassifier(n_estimators=100, random_state=self.random_state),
            "Gradient Boosting": GradientBoostingClassifier(random_state=self.random_state),
            "KNeighbors Classifier": KNeighborsClassifier(),
            "SVC": SVC(probability=True, random_state=self.random_state),
            "Linear SVC": LinearSVC(max_iter=10000, random_state=self.random_state)
        }

    def _prepare_data(self):
        X = self.df[self.feature_cols]
        y = self.df[self.target_col].astype(int)
        self.X_train, self.X_test, self.y_train, self.y_test = train_test_split(
            X, y, test_size=self.test_size, random_state=self.random_state, shuffle=True
        )

        self.preprocessor = ColumnTransformer(transformers=[
            ('cat', OneHotEncoder(handle_unknown='ignore'), self.cat_features),
            ('num', StandardScaler(), self.num_features)
        ])

    def evaluate_models(self):
        for name, clf in self.models.items():
            print(f"\n🔎 模型評估：{name}")

            pipeline = Pipeline(steps=[
                ('preprocessor', self.preprocessor),
                ('classifier', clf)
            ])

            pipeline.fit(self.X_train, self.y_train)
            y_pred = pipeline.predict(self.X_test)

            try:
                y_pred_prob = pipeline.predict_proba(self.X_test)[:, 1]
                auc = roc_auc_score(self.y_test, y_pred_prob)
            except AttributeError:
                auc = None

            conf_matrix = confusion_matrix(self.y_test, y_pred)
            tn, fp, fn, tp = conf_matrix.ravel()
            accuracy = accuracy_score(self.y_test, y_pred)
            precision = precision_score(self.y_test, y_pred, zero_division=0)
            recall = recall_score(self.y_test, y_pred, zero_division=0)
            f1 = f1_score(self.y_test, y_pred, zero_division=0)
            specificity = tn / (tn + fp) if (tn + fp) > 0 else 0.0

            print(f"準確度 (Accuracy): {accuracy:.4f}")
            print(f"精確率 (Precision): {precision:.4f}")
            print(f"召回率 (Sensitivity): {recall:.4f}")
            print(f"F1 分數: {f1:.4f}")
            print(f"特異度 (Specificity): {specificity:.4f}")
            if auc is not None:
                print(f"ROC AUC 分數: {auc:.4f}")
            else:
                print("⚠️ 此模型不支援 ROC AUC（無 predict_proba）")
            print(f"混淆矩陣:\n{conf_matrix}")
            print("-" * 60)

            self.results.append({
                "Model": name,
                "Accuracy": accuracy,
                "Precision": precision,
                "Sensitivity (Recall)": recall,
                "F1 Score": f1,
                "Specificity": specificity,
                "ROC AUC": auc if auc is not None else "N/A",
                "TP": tp,
                "TN": tn,
                "FP": fp,
                "FN": fn
            })

    def export_results(self, output_path="model_evaluation_results.xlsx"):
        results_df = pd.DataFrame(self.results)
        results_df.to_excel(output_path, index=False)
        print(f"✅ 模型評估結果已輸出為 Excel 檔案：{output_path}")
