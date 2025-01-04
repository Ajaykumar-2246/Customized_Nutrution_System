import os
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

# Get current directory and construct the absolute file path for 'recipes.csv'
current_dir = os.path.dirname(os.path.abspath(__file__))
file_path = os.path.join(current_dir, 'recipes.csv')

# Debugging: Check if the file path exists
st.write("Current working directory:", os.getcwd())
st.write("File path exists:", os.path.exists(file_path))

# Load and preprocess the dataset
try:
    data = pd.read_csv(file_path, encoding='utf-8', delimiter=',')  # Handle encoding
    data.columns = data.columns.str.lower()  # Convert all column names to lowercase
except FileNotFoundError:
    st.error("File 'recipes.csv' not found. Please ensure the file is in the same directory as 'app.py'.")
    st.stop()
except Exception as e:
    st.error(f"An error occurred while reading the dataset: {str(e)}")
    st.stop()

# Required columns for processing
columns_to_keep = [
    "recipeid",
    "name",
    "description",
    "recipecategory",
    "recipeingredientparts",
    "calories",
    "fatcontent",
    "saturatedfatcontent",
    "cholesterolcontent",
    "sodiumcontent",
    "carbohydratecontent",
    "fibercontent",
    "sugarcontent",
    "proteincontent",
]

# Check for missing columns
required_columns = set(columns_to_keep)
missing_columns = required_columns - set(data.columns)
if missing_columns:
    st.error(f"Missing columns in dataset: {missing_columns}")
    st.write("Dataset Columns Found:", data.columns.tolist())
    st.stop()

# Select and preprocess relevant columns
data = data[columns_to_keep]

# Convert relevant columns to numeric
numeric_columns = [
    "calories",
    "fatcontent",
    "saturatedfatcontent",
    "cholesterolcontent",
    "sodiumcontent",
    "carbohydratecontent",
    "fibercontent",
    "sugarcontent",
    "proteincontent",
]
for col in numeric_columns:
    data[col] = pd.to_numeric(data[col], errors="coerce")

# Drop rows with NaN values in key columns
data = data.dropna(subset=numeric_columns)

# Function to Calculate Calorie Needs
def calculate_calories(age, gender, weight, height, goal):
    # Mifflin-St Jeor Equation
    if gender == "male":
        bmr = 10 * weight + 6.25 * height - 5 * age + 5
    else:
        bmr = 10 * weight + 6.25 * height - 5 * age - 161

    # Adjust for Goal
    if goal == "weight loss":
        return bmr - 500  # Calorie deficit
    elif goal == "muscle gain":
        return bmr + 500  # Calorie surplus
    else:
        return bmr  # Maintenance calories

# Function to Calculate BMI
def calculate_bmi(weight, height):
    # BMI Formula: weight (kg) / (height (m))^2
    height_m = height / 100  # Convert height to meters
    bmi = weight / (height_m ** 2)
    return bmi

# Generate Meal Plan
def generate_meal_plan(calorie_needs, data):
    # Split calorie needs across meals
    meal_calories = {
        "breakfast": calorie_needs * 0.3,  # 30% for breakfast
        "lunch": calorie_needs * 0.4,      # 40% for lunch
        "dinner": calorie_needs * 0.3      # 30% for dinner
    }

    # Define macro targets per meal
    macro_targets = {
        meal: {
            "protein": (calories * 0.2) / 4,  # 20% protein
            "carbs": (calories * 0.5) / 4,   # 50% carbs
            "fat": (calories * 0.3) / 9      # 30% fat
        }
        for meal, calories in meal_calories.items()
    }

    # Generate meal plans
    meal_plan = {}
    meal_totals = {}  # Store total calories for each meal
    used_recipes = []  # List to store used recipe IDs for diversity across meals

    for meal, targets in macro_targets.items():
        # Calculate scores for recipes
        data["score"] = (
            abs(data["proteincontent"] - targets["protein"]) +
            abs(data["carbohydratecontent"] - targets["carbs"]) +
            abs(data["saturatedfatcontent"] - targets["fat"])
        )

        # Select top recipes for the meal
        selected_recipes = data.sort_values("score").head(6)  # Select 5-6 items per meal

        # Remove any recipes that have already been used in previous meals
        selected_recipes = selected_recipes[~selected_recipes["recipeid"].isin(used_recipes)]

        # If fewer than 5 recipes remain, allow some overlap from previous meals
        if selected_recipes.shape[0] < 5:
            remaining_needed = 5 - selected_recipes.shape[0]
            remaining_recipes = data[data["recipeid"].isin(used_recipes)].head(remaining_needed)
            selected_recipes = pd.concat([selected_recipes, remaining_recipes])

        # Add selected recipes' IDs to the used list
        used_recipes.extend(selected_recipes["recipeid"].tolist())

        meal_plan[meal] = selected_recipes  # Store the full dataframe for meal

        # Calculate total calories for this meal
        total_calories = (
            selected_recipes["proteincontent"] * 4 +
            selected_recipes["carbohydratecontent"] * 4 +
            selected_recipes["saturatedfatcontent"] * 9
        ).sum()
        meal_totals[meal] = total_calories

    return meal_plan, meal_totals

# Visualize Calories Per Meal
def visualize_meal_calories(meal_totals):
    meals = list(meal_totals.keys())
    calories = list(meal_totals.values())

    plt.figure(figsize=(5, 3))  # Adjusted figure size
    plt.bar(meals, calories, color=['blue', 'green', 'red'])
    plt.xlabel("Meals", fontsize=6)  # Adjusted font size for x-axis
    plt.ylabel("Calories", fontsize=6)  # Adjusted font size for y-axis
    plt.title("Calories Per Meal", fontsize=6)  # Adjusted font size for title
    st.pyplot(plt)

# Streamlit App
st.title("Customized Nutrition System")
st.write("This app generates a personalized meal plan based on your dietary needs and preferences.")
# Add two <> tags below the title
st.write("Here you can view the sample meal plan along with details such as calories and macro breakdown.")


# Input form
with st.form(key='meal_plan_form'):
    age = st.number_input("Enter your age:", min_value=2, max_value=120, step=1)
    gender = st.selectbox("Select your gender:", ["Male", "Female"], index=0)
    weight = st.number_input("Enter your weight (kg):", min_value=10.0, max_value=300.0, step=0.1)
    height = st.number_input("Enter your height (cm):", min_value=50.0, max_value=250.0, step=0.1)
    goal = st.selectbox("Select your goal:", ["Weight loss", "Maintenance", "Muscle gain"], index=1)

    submit_button = st.form_submit_button("Generate Meal Plan")

# Calculate BMI and Calorie Needs based on input or defaults
bmi = calculate_bmi(weight, height)
calorie_needs = calculate_calories(age, gender.lower(), weight, height, goal.lower())

# Generate Meal Plan and Visualize Results
meal_plan, meal_totals = generate_meal_plan(calorie_needs, data)

# Always display results
st.subheader(f"Your BMI is: {bmi:.2f}")
st.subheader("Generated Meal Plan")
for meal, recipes in meal_plan.items():
    st.write(f"**{meal.capitalize()}**")
    st.table(recipes[["name"]].head(5).reset_index(drop=True))

st.subheader("Calories Per Meal")
visualize_meal_calories(meal_totals)
