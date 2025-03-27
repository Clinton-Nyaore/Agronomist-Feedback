import streamlit as st
from streamlit_option_menu import option_menu
from supabase import create_client
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import altair as alt
import plotly.express as px
import bcrypt

# Load environment variables
SUPABASE_URL = st.secrets["supabase"]["url"]
SUPABASE_KEY = st.secrets["supabase"]["api_key"]

# Initialize Supabase client
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Retrieve credentials
USERNAME = st.secrets["auth"]["username"]
PASSWORD_HASH = st.secrets["auth"]["password_hash"].encode()  # Convert to bytes for bcrypt

#########################################
#### Page Configuration
st.set_page_config(
    page_title="Rhea - Agronomist Feedback System",
    page_icon="🌾",
    layout="wide",
    initial_sidebar_state="expanded"
    )
#########################################

#########################################
#### CSS Style
st.markdown(
    """
    <style>
        /* Style the title */
        .title {
            font-size: 36px;
            font-weight: bold;
            color: #2c3e50;
            text-align: center;
            margin-bottom: 20px;
        }
        
        /* Style the table */
        .dataframe {
            border-collapse: collapse;
            width: 100%;
            border: 1px solid #ddd;
            font-size: 14px;
        }
        .dataframe th {
            background-color: #2c3e50;
            color: white;
            text-align: left;
            padding: 10px;
            border-bottom: 2px solid #ddd;
        }
        .dataframe td {
            padding: 10px;
            border-bottom: 1px solid #ddd;
        }
        .dataframe tr:nth-child(even) {
            background-color: #f2f2f2;
        }
        .dataframe tr:hover {
            background-color: #d1ecf1;
        }
        
        /* Style the button */
        .stButton>button {
            background-color: #27ae60;
            color: white;
            border-radius: 8px;
            font-size: 16px;
            padding: 10px;
        }
        .stButton>button:hover {
            background-color: white;
        }
    </style>
    """,
    unsafe_allow_html=True,
)
#########################################

#########################################
#### Functions
# Fetch data from Supabase
@st.cache_data(ttl=60)
def fetch_data():
    response = supabase.table("crop_predictions").select("*").execute()
    if response and response.data:
        return pd.DataFrame(response.data)
    st.warning("No data available from Supabase.")
    return pd.DataFrame()

# Clean the data
def clean_data(df):
    """
    Cleans the input dataframe by:
    - Removing duplicates
    - Standardizing location names
    - Filtering out test locations (e.g., Nairobi)
    - Converting 'created_at' to datetime with the correct format and timezone (EAT)
    """
    # Create a copy of the dataframe
    clean_df = df.copy()

    # Drop duplicates based on key measurement columns
    clean_df.drop_duplicates(subset=["N", "P", "K", "Temperature", "Humidity", "pH", "Rainfall", "Latitude", "Longitude", "Crop"], inplace=True)

    # Standardize location names
    clean_df["Location"] = clean_df["Location"].replace("Muranga County", "Murang'a")

    # Remove test location (Nairobi)
    clean_df = clean_df[clean_df["Location"] != "Nairobi County"]

    # Convert 'created_at' to datetime
    clean_df["created_at"] = pd.to_datetime(clean_df["created_at"])

    # Check if the column is timezone-aware
    if clean_df["created_at"].dt.tz is None:
        # If not timezone-aware, localize to UTC first
        clean_df["created_at"] = clean_df["created_at"].dt.tz_localize("UTC")

    # Convert to East Africa Time (EAT, UTC+3)
    clean_df["created_at"] = clean_df["created_at"].dt.tz_convert("Africa/Nairobi")

    # Extract formatted date and time separately
    clean_df["date"] = clean_df["created_at"].dt.strftime("%Y-%m-%d")  # YYYY-MM-DD format
    clean_df["time_eat"] = clean_df["created_at"].dt.strftime("%H:%M:%S")  # HH:MM:SS format

    return clean_df

# Authenticate the user first 
def login():
    """Single-user login system using a hashed password"""
    st.title("Login Page")

    # Input fields
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    # Login button
    if st.button("Login"):
        if username == USERNAME and bcrypt.checkpw(password.encode(), PASSWORD_HASH) == 1:
            st.success(f"Welcome {USERNAME}!")
            st.session_state["authenticated"] = True
        else:  
            st.error("Invalid username or password")
#########################################
# Check authentication
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    login()
else:
    #########################################
    #### Sidebar
    with st.sidebar:
        selected = option_menu(
            menu_title = "Rhea", 
            menu_icon = "cast",
            options = ["Home", "Feedback", "Logout"],
            icons = ["house", "pencil-square", "box-arrow-left"]
            )
    #########################################

        ### Main Pages ####
    ########################################
    #### Home Page
    if selected == "Home":
        st.markdown('<div class="title">Rhea Soil Data Analysis</div>', unsafe_allow_html=True)

        # Fetch data from Supabase
        df = fetch_data()
        cleaned_df = clean_data(df) # Clean the data
    
        # Create columns
        col1, col2 = st.columns([2, 2])

        # Column 1: Total Records
        with col1:
            st.subheader("Total Records")
            st.markdown(
                f"""
                <div style="
                    background-color: #f8f9fa;
                    padding: 20px;
                    border-radius: 10px;
                    box-shadow: 2px 2px 10px rgba(0, 0, 0, 0.1);
                    text-align: center;
                ">
                    <h3 style="color: #333;">Total Records</h3>
                    <p style="font-size: 24px; font-weight: bold; color: #007BFF;">{df.shape[0]} samples</p>
                </div>
                """,
                unsafe_allow_html=True
            )

            # 🗺️ Interactive Soil Test Locations Map
            st.subheader("🌍 Soil Test Locations in East Africa")

            # Remove missing lat/lon values
            map_df = cleaned_df.dropna(subset=["Latitude", "Longitude"])

            # Allow users to select a location
            location_options = ["All Locations"] + list(map_df["Location"].unique())
            selected_location = st.selectbox("📍 Select a Location", location_options)

            # Filter data based on user selection
            if selected_location != "All Locations":
                map_df = map_df[map_df["Location"] == selected_location]

            # Create an interactive Plotly map with LARGE pins
            map_fig = px.scatter_mapbox(
                map_df,
                lat="Latitude",
                lon="Longitude",
                hover_name="Location",
                hover_data={"Latitude": True, "Longitude": True, "Crop": True, "pH": True},  # Show extra details
                color_discrete_sequence=["red"],  # Pin color
                title="Soil Test Locations in Kenya & Tanzania"
            )

            # Make the pins BIG and VISIBLE
            map_fig.update_traces(
                marker=dict(
                    size=15,  # **Increased Pin Size**
                    color="red",
                    symbol="circle",
                    opacity=0.9  # Slight transparency for better visualization
                )
            )

            # Improve map appearance
            map_fig.update_layout(
                mapbox_style="open-street-map",  # Better map details
                mapbox_center={"lat": -2.0, "lon": 37.0},  # Center on East Africa
                mapbox_zoom=6,  # Adjusted zoom level
                margin=dict(l=10, r=10, t=40, b=10),
                height=500  # Adjusted for better UI fit
            )

            # Show the interactive map in Streamlit
            st.plotly_chart(map_fig, use_container_width=True)
        
        # Column 2: Location-based test
        with col2:
            st.subheader("Tests Per Location")

            # Remove missing and invalid locations
            cleaned_df = cleaned_df[~cleaned_df["Location"].isin(["N/A", "Not found", None])]

            # Add "All Locations" option
            location_options = ["All Locations"] + list(cleaned_df["Location"].unique())
            location = st.selectbox("Select Location", location_options)

            # Filter data based on selection
            if location == "All Locations":
                location_counts = cleaned_df["Location"].value_counts().reset_index()
                location_counts.columns = ["Location", "Tests"]
            else:
                location_df = cleaned_df[cleaned_df["Location"] == location]
                location_counts = location_df["Location"].value_counts().reset_index()
                location_counts.columns = ["Location", "Tests"]

            # Check if data is available
            if location_counts.empty:
                st.warning(f"No tests recorded for {location}.")
            else:
                # Create interactive Plotly bar chart
                fig = px.bar(
                    location_counts,
                    x="Location",
                    y="Tests",
                    color="Location",  # Distinct color per location
                    title="Tests Conducted Across Locations" if location == "All Locations" else f"Tests Conducted in {location}",
                    labels={"Location": "Location", "Tests": "Number of Tests"},
                    color_discrete_sequence=px.colors.qualitative.Vivid,  # Beautiful color scheme
                    text_auto=True,  # Show values on bars
                )

                # Improve layout
                fig.update_layout(
                    xaxis_tickangle=-30,  # Rotate labels for readability
                    xaxis_title="Location",
                    yaxis_title="Number of Tests",
                    title_font=dict(size=16, family="Arial", color="black"),
                    plot_bgcolor="rgba(0,0,0,0)",  # Transparent background
                    paper_bgcolor="rgba(0,0,0,0)",
                    legend_title="Location",
                    margin=dict(l=40, r=40, t=40, b=40),
                )

                # Show chart in Streamlit
                st.plotly_chart(fig, use_container_width=True)
            
            # Scatter plot for test dates
            st.subheader("Soil Test Dates by County (EAT Time)")

            # Convert `created_at` to datetime (UTC)
            cleaned_df["created_at"] = pd.to_datetime(cleaned_df["created_at"], utc=True)

            # Convert to East Africa Time (EAT, UTC+3)
            cleaned_df["created_at_eat"] = cleaned_df["created_at"].dt.tz_convert("Africa/Nairobi")

            # Create scatter plot
            scatter_fig = px.scatter(
                cleaned_df,
                x="date",
                y="Location",
                color="Location",  # Differentiate by color
                hover_data={"created_at_eat": True, "time_eat": True, "Location": False},  # Show EAT time on hover
                title="Soil Test Dates by County (EAT Time)",
            )

            # Adjust marker size and background
            scatter_fig.update_traces(marker=dict(size=8))  # Reduce marker size

            scatter_fig.update_layout(
                xaxis_title="Date",
                yaxis_title="County",
                hovermode="closest",
                width=800,  # Reduced width
                height=450,  # Reduced height
                margin=dict(l=20, r=20, t=40, b=40),
                font=dict(size=10),
                plot_bgcolor="rgba(0,0,0,0)",  # Transparent plot background
                paper_bgcolor="rgba(0,0,0,0)",  # Transparent outer background
            )

            # Display scatter plot
            st.plotly_chart(scatter_fig, use_container_width=True)

    ########################################
    #### Feedback Page
    elif selected == "Feedback":
        # Title
        st.markdown('<div class="title">Rhea - Agronomist Feedback System</div>', unsafe_allow_html=True)

        # Fetch data from Supabase
        df = fetch_data()
        cleaned_df = clean_data(df)

        # Display data in an editable format
        if not df.empty:
            st.subheader("Crop Recommendations")
            st.subheader("Just edit the 'Feedback Message' column and click 'Submit Feedback' to update the feedback.")

            df_filtered = cleaned_df[[
                "Prediction_ID", "created_at", "N", "P", "K", "Temperature", "Humidity", "Rainfall", "Location", "Crop", "User_Selected_Crop", "Feedback_Message",
            ]].copy()
            
            df_filtered.rename(columns={
                "Prediction_ID": "ID",
                "created_at": "Date",
                "N": "Nitrogen",
                "P": "Phosphorus",
                "K": "Potassium",
                "Temperature": "Temperature (°C)",
                "Humidity": "Humidity (%)",
                "Rainfall": "Rainfall (mm)",
                "Crop": "Recommended Crop",
                "User_Selected_Crop": "Farmer Selected Crop",
                "Feedback_Message": "Feedback Message"
            }, inplace=True)
            
            
            edited_df = st.data_editor(df_filtered, num_rows="dynamic", use_container_width=True)

            if st.button("Submit Feedback"):
                for index, row in edited_df.iterrows():
                    try:
                        prediction_id = int(row["ID"])
                    except ValueError:
                        st.error(f"Invalid Prediction_ID: {row['ID']}")
                        continue

                    selected_crop = row["Farmer Selected Crop"] if row["Farmer Selected Crop"] else None
                    feedback_message = row["Feedback Message"] if row["Feedback Message"] else None

                    update_data = {}
                    if selected_crop:
                        update_data["User_Selected_Crop"] = selected_crop
                    if feedback_message:
                        update_data["Feedback_Message"] = feedback_message
                        update_data["Feedback_Received"] = True

                    if update_data:
                        response = supabase.table("crop_predictions").update(update_data).eq("Prediction_ID", prediction_id).execute()
                        response_dict = response.model_dump()
                        
                        if "error" in response_dict and response_dict["error"]:  
                            st.error(f"Failed to update feedback for {prediction_id}: {response_dict['error']}")
                        else:
                            st.success(f"Feedback submitted for Prediction_ID: {prediction_id}")
        else:
            st.warning("No data available from Supabase.")
    ########################################

    ########################################
    #### Logout Button
    elif selected == "Logout":
        st.session_state["authenticated"] = False