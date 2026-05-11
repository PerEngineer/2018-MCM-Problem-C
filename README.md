# 2018 MCM Problem C 能源画像建模报告

本仓库整理了 2018 年美国大学生数学建模竞赛 Problem C 的中文建模报告、分析代码和主要结果文件。

## 文件结构

- `2018_MCM_Problem_C.pdf`：题目文件。
- `2018_MCM_Problem_C_Data.xlsx`：题目给定数据集。
- `analysis_2018c.py`：数据读取、指标计算、评价模型和预测模型代码。
- `make_figures.py`：根据计算结果生成报告图表。
- `outputs/2018C_solution_CN.tex`：中文建模报告 LaTeX 源码。
- `outputs/2018C_solution_CN.pdf`：中文建模报告 PDF。
- `outputs/summary_sheet_CN.tex`、`outputs/summary_sheet_CN.pdf`：One-page Summary Sheet。
- `outputs/governors_memo_CN.tex`、`outputs/governors_memo_CN.pdf`：One-page memo。
- `outputs/*.csv`、`outputs/analysis_summary.json`：模型计算结果。
- `outputs/figures/*.pdf`：报告中使用的图表。

## 复现方法

先安装 Python 依赖：

```bash
pip install -r requirements.txt
```

重新生成数据结果：

```bash
python analysis_2018c.py
```

重新生成图表：

```bash
python make_figures.py
```

重新编译主报告：

```bash
xelatex -interaction=nonstopmode -halt-on-error -output-directory=outputs outputs/2018C_solution_CN.tex
xelatex -interaction=nonstopmode -halt-on-error -output-directory=outputs outputs/2018C_solution_CN.tex
```

如果只需要查看结果，直接打开 `outputs/2018C_solution_CN.pdf` 即可。

## 说明

报告主体、Summary Sheet 和 memo 已经分开保存，便于分别提交或展示。LaTeX 编译产生的 `.aux`、`.log`、`.toc` 等临时文件没有放入本整理版文件夹。
