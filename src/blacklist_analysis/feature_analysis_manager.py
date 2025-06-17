import pandas as pd
import numpy as np
from scipy.stats import chi2_contingency, ttest_ind
import seaborn as sns
import matplotlib.pyplot as plt

class FeatureAnalysisManager:
    def __init__(self, dataframe, label_col="good/bad"):
        self.df = dataframe.copy()
        self.label_col = label_col
        self.label_numeric_col = "label"
        self.significant_categorical = []
        self.significant_numerical = []
        self.excluded_columns = set([
            "whois_success", "whois_hasdata", "url", "domain", "source", "date", 
            "register time", "remaining time", "total life time", 
            "last update", "found_date", "download_date", "updated_date"
        ])
        self.exclude_datetime_columns()
        self._prepare_data()
    
    def exclude_datetime_columns(self):
        datetime_cols = [col for col in self.df.columns if np.issubdtype(self.df[col].dtype, np.datetime64)]
        self.excluded_columns.update(datetime_cols)

    def _prepare_data(self):
        for col in self.df.columns:
            if self.df[col].dtype in ['object', 'bool']:
                self.df[col] = self.df[col].fillna("missing")
            else:
                self.df[col] = self.df[col].fillna(-1)

        # Convert label column to numeric
        self.df[self.label_numeric_col] = self.df[self.label_col].astype(int)

    def analyze_categorical_features(self):
        print("=== 類別型欄位 卡方檢定 ===")
        for col in self.df.columns:
            if col in self.excluded_columns or col == self.label_col:
                continue

            if self.df[col].dtype in ['object', 'bool']:
                try:
                    self.df[col] = self.df[col].astype(str)
                    crosstab = pd.crosstab(self.df[col], self.df[self.label_col])
                    if crosstab.shape[0] > 1 and crosstab.shape[1] > 1:
                        chi2, p, dof, expected = chi2_contingency(crosstab)
                        print(f"--- Column: {col} ---")
                        print("Chi-square =", chi2)
                        print("p-value =", p)
                        if p < 0.05:
                            print(f"=> '{col}' 與 {self.label_col} 有顯著關聯")
                            print("比例分布：")
                            ratio = crosstab.apply(lambda x: x / x.sum(), axis=1)
                            print(ratio)
                            self.significant_categorical.append(col)
                        else:
                            print(f"=> '{col}' 與 {self.label_col} 無顯著關聯")
                    else:
                        print(f"[跳過] 欄位 {col} 的交叉表不足兩列或兩欄")
                except Exception as e:
                    print(f"[錯誤] 欄位 {col}：{e}")
                print()

    def analyze_numerical_features(self):
        print("\n=== 數值型欄位 T-test ===")
        numerical_cols = [
            col for col in self.df.select_dtypes(include=["int64", "float64"]).columns 
            if col not in [self.label_col, self.label_numeric_col]
        ]

        for col in numerical_cols:
            group1 = self.df[self.df[self.label_numeric_col] == 1][col]
            group0 = self.df[self.df[self.label_numeric_col] == 0][col]
            if len(group1) > 1 and len(group0) > 1:
                t_stat, p = ttest_ind(group1, group0, equal_var=False)
                print(f"--- Column: {col} ---")
                print("T-statistic =", t_stat)
                print("p-value =", p)
                if p < 0.05:
                    print(f"=> '{col}' 與 {self.label_col} 有顯著關聯")
                    self.significant_numerical.append(col)
                else:
                    print(f"=> '{col}' 與 {self.label_col} 無顯著關聯")

        # Heatmap
        plt.figure(figsize=(10, 8))
        corr = self.df[numerical_cols + [self.label_numeric_col]].corr()
        sns.heatmap(corr, annot=True, cmap="coolwarm", fmt=".2f")
        plt.title(f"Heatmap of Numerical Features vs {self.label_col}")
        plt.tight_layout()
        plt.show()

    def analyze_time_features(self, time_cols):
        print("\n=== 時間欄位分析 ===")
        for col in time_cols:
            if col not in self.df.columns:
                continue
            print(f"\n--- 分析欄位：{col} ---")

            plt.figure(figsize=(8, 5))
            sns.boxplot(data=self.df, x=self.label_col, y=col, palette=["red", "green"])
            plt.xticks([0, 1], ["Bad", "Good"])
            plt.title(f"Boxplot of '{col}' by {self.label_col}")
            plt.grid(True)
            plt.show()

            plt.figure(figsize=(8, 5))
            sns.kdeplot(data=self.df[self.df[self.label_numeric_col] == 0], x=col, label="Bad", fill=True, color="red", alpha=0.4)
            sns.kdeplot(data=self.df[self.df[self.label_numeric_col] == 1], x=col, label="Good", fill=True, color="green", alpha=0.4)
            plt.title(f"KDE Plot of '{col}' by {self.label_col}")
            plt.xlabel(col)
            plt.legend()
            plt.grid(True)
            plt.show()

            good_vals = self.df[self.df[self.label_numeric_col] == 1][col]
            bad_vals = self.df[self.df[self.label_numeric_col] == 0][col]
            print("Good URL 描述統計：")
            print(good_vals.describe())
            print("Bad URL 描述統計：")
            print(bad_vals.describe())

# 使用方式範例
if __name__ == "__main__":
    df_alldata = pd.read_excel("./src/data/database/all_url_good_and_bad_new.xlsx")
    print("Original data shape: ", df_alldata.shape)

    df_filtered = df_alldata[(df_alldata["whois_success"] == True) & (df_alldata["whois_hasdata"] == True)]
    print("Filtered data shape: ", df_filtered.shape)

    fam = FeatureAnalysisManager(df_filtered)
    fam.analyze_categorical_features()
    fam.analyze_numerical_features()
    fam.analyze_time_features(["register time", "remaining time", "total life time"])
