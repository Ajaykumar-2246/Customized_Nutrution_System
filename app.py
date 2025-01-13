import os
import streamlit as st
import pandas as pd
import random

# Get current directory and construct the absolute file path for 'recipes.csv'
current_dir = os.path.dirname(os.path.abspath(__file__))
file_path = os.path.join(current_dir, 'recipes.csv')

# Debugging: Check if the file path exists
# st.write("Current working directory:", os.getcwd())
# st.write("File path exists:", os.path.exists(file_path))

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

# Function to Calculate BMI and Category
def calculate_bmi(weight, height):
    # BMI Formula: weight (kg) / (height (m))^2
    height_m = height / 100  # Convert height to meters
    bmi = weight / (height_m ** 2)

    # BMI categories
    if bmi < 18.5:
        bmi_category = "Underweight"
    elif 18.5 <= bmi < 24.9:
        bmi_category = "Normal weight"
    elif 25 <= bmi < 29.9:
        bmi_category = "Overweight"
    else:
        bmi_category = "Obesity"

    return bmi, bmi_category

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
    used_recipes = set()  # Set to track used recipes and avoid duplication
    recipe_usage_count = {}  # Dictionary to track how often each recipe has been used

    for meal, targets in macro_targets.items():
        # Calculate scores for recipes based on macros
        data["score"] = (
            abs(data["proteincontent"] - targets["protein"]) +
            abs(data["carbohydratecontent"] - targets["carbs"]) +
            abs(data["saturatedfatcontent"] - targets["fat"])
        )

        # Select a larger pool of recipes for diversity
        potential_recipes = data.sort_values("score").head(20)  # Top 20 recipes for more variety

        # Filter out already used recipes across meals
        potential_recipes = potential_recipes[~potential_recipes["recipeid"].isin(used_recipes)]

        # If fewer than 5 recipes are available, allow some overlap from previously used ones
        if potential_recipes.shape[0] < 5:
            remaining_needed = 5 - potential_recipes.shape[0]
            # Randomly select recipes from already used ones to fill in the gap
            additional_recipes = data[data["recipeid"].isin(used_recipes)].sample(remaining_needed)
            potential_recipes = pd.concat([potential_recipes, additional_recipes])

        # Track usage frequency across all meals
        for recipe_id in potential_recipes["recipeid"]:
            recipe_usage_count[recipe_id] = recipe_usage_count.get(recipe_id, 0) + 1

        # Filter out recipes that have already been used too many times across meals
        potential_recipes = potential_recipes[potential_recipes["recipeid"].map(lambda x: recipe_usage_count[x] <= 2)]

        # Randomly shuffle selected recipes to ensure variety
        selected_recipes = potential_recipes.sample(n=5, random_state=42)

        # Add selected recipes' IDs to the used list
        used_recipes.update(selected_recipes["recipeid"].tolist())

        meal_plan[meal] = selected_recipes  # Store the full dataframe for each meal

    return meal_plan

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
if submit_button:
    bmi, bmi_category = calculate_bmi(weight, height)
    calorie_needs = calculate_calories(age, gender.lower(), weight, height, goal.lower())

    # Generate Meal Plan and Visualize Results
    meal_plan = generate_meal_plan(calorie_needs, data)

    # Always display results
    st.subheader(f"CALCULATED BMI")
    st.markdown(f"Body Mass Index (BMI)")
    st.markdown(f"<span style=' margin:0px; font-size:24px;'>{bmi:.2f} </span> kg/m²", unsafe_allow_html=True)
    st.markdown(f"<span style='color:red'>{bmi_category}</span>", unsafe_allow_html=True)
    
    st.subheader("Generated Meal Plan")
    for meal, recipes in meal_plan.items():
        st.write(f"**{meal.capitalize()}**")
        st.table(recipes[["name"]].head(5).reset_index(drop=True))
