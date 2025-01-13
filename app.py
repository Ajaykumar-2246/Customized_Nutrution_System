import os
import streamlit as st
import pandas as pd
import random
from sklearn.ensemble import RandomForestRegressor

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

# Function to train a Random Forest model to predict recipe score based on input features
def train_random_forest_model(data):
    # Feature columns (ignoring non-numeric columns for simplicity)
    feature_columns = [
        "calories", "fatcontent", "saturatedfatcontent", "cholesterolcontent",
        "sodiumcontent", "carbohydratecontent", "fibercontent", "sugarcontent", "proteincontent"
    ]
    
    # Target: a custom score or label for the meal plan (could be user-specific or randomized for now)
    target = data["calories"]  # You could customize the target based on specific goals

    # Train Random Forest Regressor model
    model = RandomForestRegressor(n_estimators=100, random_state=42)
    model.fit(data[feature_columns], target)
    return model

# Generate Meal Plan using Random Forest for predictions
def generate_meal_plan_rf(calorie_needs, data, model):
    meal_calories = {
        "breakfast": calorie_needs * 0.3,  # 30% for breakfast
        "lunch": calorie_needs * 0.4,      # 40% for lunch
        "dinner": calorie_needs * 0.3      # 30% for dinner
    }

    meal_plan = {}
    used_recipes = set()

    for meal, target_calories in meal_calories.items():
        # Predict recipe score using Random Forest
        data["predicted_score"] = model.predict(data[numeric_columns])

        # Select top recipes based on predicted score
        top_recipes = data.sort_values("predicted_score", ascending=False).head(10)

        # Avoid duplicate recipes across meals
        top_recipes = top_recipes[~top_recipes["recipeid"].isin(used_recipes)]

        # If there are fewer than 5 recipes left after filtering, select as many as possible
        if len(top_recipes) < 4:
            top_recipes = data[~data["recipeid"].isin(used_recipes)].head(5)

        # Add selected recipes to meal plan
        meal_plan[meal] = top_recipes.head(4)
        used_recipes.update(top_recipes["recipeid"])

    return meal_plan

# Streamlit App
st.title("Customized Nutrition System")
st.write("This app generates a personalized meal plan based on your dietary needs and preferences.")
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

    # Train Random Forest model (you could also train the model once on app startup)
    model = train_random_forest_model(data)

    # Generate Meal Plan using Random Forest
    meal_plan = generate_meal_plan_rf(calorie_needs, data, model)

    # Display BMI and Meal Plan
    st.subheader(f"CALCULATED BMI")
    st.markdown(f"<span style=' margin:0px; padding:0px; font-size:14px;'>Body Mass Index(BMI) </span>", unsafe_allow_html=True)
    st.markdown(f"<span style=' margin:0px; font-size:26px;'>{bmi:.2f} </span> kg/m²", unsafe_allow_html=True)
    st.markdown(f"<span style='color:red; font-size:20px; margin:0px'>{bmi_category}</span>", unsafe_allow_html=True)
    
    st.subheader("Generated Meal Plan")
    for meal, recipes in meal_plan.items():
        st.write(f"**{meal.capitalize()}**")
        st.table(recipes[["name"]].reset_index(drop=True))  # Display only the recipe names
