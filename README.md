
# Bored No More: Proposal for Doing Things

![Demo](./lib/img/demo.gif)

Welcome to the *Bored No More* project! This application offers activity recommendations tailored to your current location, available free time, and weather conditions, helping you find fun ways to spend your day. The project was developed by **Adrián Benítez Rueda**.

## Table of Contents

1. [Introduction](#introduction)
2. [Features](#features)
3. [Data Sources](#data-sources)
4. [Setup](#setup)
5. [How to Use](#how-to-use)
6. [Future Improvements](#future-improvements)
7. [Beta Version](#beta-version)
8. [License](#license)

## Introduction

The *Bored No More* app is a tool to combat boredom by suggesting indoor and outdoor activities. It takes into account your location, current weather conditions, and personal preferences. The goal is to make your free time enjoyable, with suggestions you can either accept, reject, or request something new.

## Features

- **Dynamic Recommendations**: Suggests activities based on your location and weather.
- **User Preferences**: Includes interactive options to either accept, dislike, or skip an activity.
- **Indoor and Outdoor Activities**: Distinguishes between activities that can be done indoors or outdoors.
- **API Integrations**:
  - Google Geolocation API: Determines user location for location-based activity suggestions.
  - AEMET API: Fetches real-time weather data to adjust activity suggestions.
  - Google Places API: Recommends nearby locations for outdoor activities.

## Data Sources

The activities are categorized into indoor and outdoor options:
- **Indoor Activities**: Located in `data/cleaned/home_activities.csv`.
- **Outdoor Activities**: Located in `data/cleaned/outdoor_activities.csv`.

The app uses geolocation to identify local options for outdoor activities.

## Setup

To set up the project on your local machine, follow these steps:

1. **Clone the repository**:
   ```bash
   git clone https://github.com/adrianbenitezrueda/borednomore.git
   cd borednomore
   ```

2. **Install dependencies**:
   Make sure you have Python installed, then install the required libraries:
   ```bash
   pip install -r requirements.txt
   ```

3. **API Keys in Streamlit Secrets**:
   Obtain API keys for Google, AEMET, and Google Places. Store them in *Streamlit secrets* as follows:
   ```plaintext
   [secrets]
   GOOGLE_API_KEY = your_google_api_key
   AEMET_API_KEY = your_aemet_api_key
   ```

4. **Run the application**:
   Start the app using Streamlit:
   ```bash
   streamlit run app.py
   ```

## How to Use

1. **Launch the App**: After setup, open the app through the Streamlit interface.
2. **Choose Your Preferences**: Specify your available time, location, and weather.
3. **Receive Recommendations**: The app suggests activities based on your preferences. Interact with the suggestion options:
   - "Voy a hacerlo" to confirm an activity.
   - "No me apetece mucho" for a fresh suggestion.
   - "No me apetece nada hacer esto" for an alternative activity.

## Future Improvements

- **Enhanced User Experience**: Add user personalization features and improve UI for a more engaging experience.
- **Advanced Filtering**: Introduce filters for activity types, complexity, or duration.
- **Recommendation System**: Incorporate machine learning for improved activity suggestions based on user history.

## Beta Version

A **BETA version** of *Bored No More* is currently under construction. This version will include task recommendations generated by ChatGPT, adding a more interactive and personalized experience to the activity suggestions. Stay tuned for updates!

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for more details.
