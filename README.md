# Technical Notes

This repository contains **two implementations** of the indicators:

* **NumPy-based implementation**
* **pandas-based implementation**

Both implementations are designed to closely replicate the behavior and logic of the original C++ version.

## Design Differences

The original C++ implementation uses the **Curiously Recurring Template Pattern (CRTP)** to achieve compile-time polymorphism. Since Python is a dynamically typed language and relies on **dynamic dispatch**, CRTP cannot be replicated in the same way.

Instead, the Python implementation uses **inheritance and virtual method dispatch**, which is the idiomatic approach in Python while preserving the overall design and behavior of the original implementation.

## Verification

Both implementations produce the expected results.

<img width="1844" height="287" alt="Indicator Output" src="https://github.com/user-attachments/assets/88bee364-b70a-47d6-bdd6-ddb65933bdbd" />

## Generating 5-Minute Candles

A Python utility script is included to generate **5-minute candles** from the provided **1-minute candle** data (`sample_data.csv`).

Before running the indicator implementations:

1. Execute the candle generation script.
2. The script will generate a new CSV containing the aggregated 5-minute candles.
3. Update the input file path (if necessary) in the indicator code to point to the generated CSV.

## Performance Observations

Based on my observations:

* The **NumPy implementation** provides better overall performance and is better suited for this indicator computation.
* A **pandas implementation** is also included for users who prefer working with DataFrames.
* Both implementations follow the same underlying algorithm and maintain the same algorithmic time complexity as the original C++ implementation.

## Goal

The primary objective of this project was to port the C++ implementation to Python while preserving:

* The original algorithmic behavior
* Comparable time complexity
* Clean and maintainable object-oriented design
* Equivalent indicator output across implementations
