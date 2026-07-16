import json
from crewai import Task


def create_hotel_task(agent, trip_context: str, weather_data: str = "", serp_data: str = "") -> Task:
    """Task for the Hotel Agent to research and recommend accommodations."""
    extra_context = ""
    if weather_data:
        extra_context += f"\n\nCurrent weather data:\n{weather_data}"
    if serp_data:
        extra_context += f"\n\nWeb search results for hotels:\n{serp_data}"

    return Task(
        description=(
            f"Trip details:\n{trip_context}{extra_context}\n\n"
            "You are a luxury hotel consultant. Research and recommend exactly 3 hotels for this trip. "
            "Use the provided search results and your knowledge.\n\n"
            "For EACH hotel, provide detailed JSON with these fields:\n"
            "- name: Hotel name\n"
            "- rating: Rating out of 5 (e.g. 4.5)\n"
            "- price_per_night: Price in USD per night\n"
            "- location: Full address or area name\n"
            "- reason: A 2-3 sentence explanation of WHY this hotel is perfect for this traveler. "
            "Mention proximity to attractions, value for money, amenities, and how it matches their interests.\n"
            "- amenities: List of 4-6 key amenities\n"
            "- description: 1-2 sentence description\n"
            "- pros: List of 3 pros\n"
            "- cons: List of 1-2 cons\n"
            "- distance_from_center: e.g. '1.2 km from city center'\n\n"
            "RULES:\n"
            "- ALL text must be PLAIN TEXT ONLY. NEVER include HTML tags (<div>, </div>, <span>, <p>, <br>, <a>, etc.) in ANY field.\n"
            "- URL fields must contain ONLY valid http:// or https:// URLs, or be empty string.\n"
            "Output ONLY a JSON array of 3 hotel objects. No markdown, no extra text."
        ),
        expected_output=(
            "A JSON array containing exactly 3 hotel recommendation objects, each with: "
            "name, rating, price_per_night, location, reason, amenities, description, pros, cons, distance_from_center"
        ),
        agent=agent,
    )


def create_attraction_task(agent, trip_context: str, serp_data: str = "") -> Task:
    """Task for the Attraction Agent to find and plan sightseeing activities."""
    extra_context = ""
    if serp_data:
        extra_context = f"\n\nWeb search results for attractions:\n{serp_data}"

    return Task(
        description=(
            f"Trip details:\n{trip_context}{extra_context}\n\n"
            "You are an expert local guide. Recommend 6-10 attractions and activities for this trip.\n\n"
            "For EACH attraction, provide detailed JSON with these fields:\n"
            "- name: Attraction name\n"
            "- description: 2-3 sentences about what it is and why it's worth visiting\n"
            "- category: Category (museum, park, landmark, food market, etc.)\n"
            "- rating: Rating out of 5\n"
            "- entry_fee: Entry fee in USD (e.g. '$25', 'Free', '€15')\n"
            "- opening_hours: e.g. '9:00 AM - 6:00 PM'\n"
            "- time_required: e.g. '2-3 hours'\n"
            "- best_time: Best time to visit (e.g. 'Early morning to avoid crowds')\n"
            "- maps_url: Google Maps search URL format (https://www.google.com/maps/search/ENCODED_NAME)\n"
            "- website_url: Official website URL\n\n"
            "Match attractions to the traveler's interests: food, history, etc. "
            "Include a mix of popular landmarks and hidden gems.\n\n"
            "RULES:\n"
            "- ALL text must be PLAIN TEXT ONLY. NEVER include HTML tags (<div>, </div>, <span>, <p>, <br>, <a>, etc.) in ANY field.\n"
            "- URL fields must contain ONLY valid http:// or https:// URLs, or be empty string.\n"
            "Output ONLY a JSON array of attraction objects. No markdown, no extra text."
        ),
        expected_output=(
            "A JSON array of 6-10 attraction objects, each with: "
            "name, description, category, rating, entry_fee, opening_hours, time_required, "
            "best_time, maps_url, website_url"
        ),
        agent=agent,
    )


def create_weather_task(agent, trip_context: str, real_weather: str = "") -> Task:
    """Task for the Weather Agent to provide climate information."""
    extra = ""
    if real_weather:
        extra = f"\n\nReal-time weather API data:\n{real_weather}"

    return Task(
        description=(
            f"Trip details:\n{trip_context}{extra}\n\n"
            "You are a travel weather specialist. Based on the real weather data above, "
            "provide a comprehensive weather report for the destination during the trip dates.\n\n"
            "Provide JSON with these fields:\n"
            "- temperature: Current temperature in Celsius (number)\n"
            "- feels_like: Feels-like temperature in Celsius (number)\n"
            "- humidity: Humidity percentage (integer)\n"
            "- condition: Short weather condition (e.g. 'Partly Cloudy')\n"
            "- description: 1-2 sentence weather description\n"
            "- wind_speed: Wind speed in m/s (number)\n"
            "- rain_chance: Rain probability percentage (integer 0-100)\n"
            "- sunrise: Sunrise time (e.g. '06:15 AM')\n"
            "- sunset: Sunset time (e.g. '08:45 PM')\n"
            "- icon: Single emoji that best represents the weather\n"
            "- suggestions: Array of 4-5 practical weather-based travel tips\n\n"
            "Use the real API data. Only guess if API data is unavailable.\n\n"
            "Output ONLY a JSON object. No markdown, no extra text."
        ),
        expected_output=(
            "A JSON object with weather data: temperature, feels_like, humidity, condition, "
            "description, wind_speed, rain_chance, sunrise, sunset, icon, suggestions"
        ),
        agent=agent,
    )


def create_budget_task(agent, trip_context: str, serp_data: str = "") -> Task:
    """Task for the Budget Agent to estimate trip costs."""
    extra_context = ""
    if serp_data:
        extra_context = f"\n\nWeb search results for prices:\n{serp_data}"

    return Task(
        description=(
            f"Trip details:\n{trip_context}{extra_context}\n\n"
            "You are a travel budget expert. Create a detailed cost estimate for this trip.\n\n"
            "Provide JSON with these fields:\n"
            "- hotel: Total hotel cost for the trip (number)\n"
            "- food: Total food cost for the trip (number)\n"
            "- transport: Total transport cost including airport transfers (number)\n"
            "- activities: Total cost for attractions and activities (number)\n"
            "- miscellaneous: Shopping, tips, emergencies (number)\n"
            "- total: Sum of all categories (number)\n"
            "- per_person: Total divided by number of travelers (number)\n"
            "- within_budget: True if total <= user budget (boolean)\n"
            "- remaining: Budget minus total (number, can be negative)\n"
            "- suggestions: Array of 3-5 specific cost-saving tips\n\n"
            "Be realistic with prices. Use actual price ranges for the destination.\n"
            "If total exceeds budget, provide specific alternatives to reduce cost.\n\n"
            "Output ONLY a JSON object. No markdown, no extra text."
        ),
        expected_output=(
            "A JSON budget object with: hotel, food, transport, activities, miscellaneous, "
            "total, per_person, within_budget, remaining, suggestions"
        ),
        agent=agent,
    )


def create_planning_task(agent, trip_context: str, num_days: int = 5) -> Task:
    """Task for the Travel Planner Agent to compile the final itinerary."""
    return Task(
        description=(
            "You are a world-class travel planner. The previous agents have completed their research.\n"
            "Their results are in your context above. Now you MUST compile everything into a SINGLE "
            "JSON object.\n\n"
            f"THE TRIP IS EXACTLY {num_days} DAYS LONG. You MUST create EXACTLY {num_days} daily_plans entries.\n"
            f"Daily plan day_number values MUST be: 1, 2, 3, ... up to {num_days}. Do NOT skip any day.\n\n"
            "CRITICAL: You MUST include ALL of these fields in your JSON output. Do NOT skip any:\n\n"
            "REQUIRED FIELDS:\n"
            "1. trip_summary (string): 3-4 sentence overview of the trip\n"
            "2. destination_overview (string): 3-4 sentences about the destination including history, best season, currency, language, timezone\n"
            "3. recommended_hotels (array of 3 objects): From the hotel agent's research above. Each with:\n"
            "   - name, rating, price_per_night, location, reason, amenities (array), description, pros (array), cons (array), distance_from_center\n"
            "4. attractions (array of 5-8 objects): From the attraction agent's research above. Each with:\n"
            "   - name, description, category, rating, entry_fee, opening_hours, time_required, best_time\n"
            f"5. daily_plans (array of EXACTLY {num_days} objects): ONE OBJECT PER DAY from day 1 to day {num_days}. Each with:\n"
            "   - day_number (integer starting at 1), title (string like 'Historic Heart of Paris'),\n"
            "   - morning (detailed activity), afternoon (detailed activity), evening (detailed activity), night (detailed activity),\n"
            "   - lunch (specific restaurant/cuisine), dinner (specific restaurant/cuisine),\n"
            "   - estimated_daily_cost (number), highlights (array of 2-3 strings)\n"
            "6. budget (object): From the budget agent above:\n"
            "   - hotel, food, transport, activities, miscellaneous, total, per_person, within_budget, remaining, suggestions (array)\n"
            "7. ai_insights (object):\n"
            "   - hidden_gems (array), tourist_traps (array), local_food (array), safety_tips (array), money_tips (array), scam_alerts (array), photography_spots (array), sunrise_spots (array)\n"
            "8. transport_options (array of 3-4 objects):\n"
            "   - mode, description, estimated_time, estimated_cost, tips\n"
            "9. restaurants (array of 4-5 objects):\n"
            "   - name, cuisine, rating, price_range, description, opening_hours, maps_url\n"
            "10. packing_checklist (object with arrays): documents, electronics, medicines, clothes, essentials\n"
            "11. travel_tips (array of 5-6 strings)\n"
            "12. best_times (array of 3-4 strings)\n"
            "13. trip_score (integer 70-95)\n\n"
            "RULES:\n"
            f"- You MUST create EXACTLY {num_days} daily_plans. Count them before outputting. If you have fewer than " + str(num_days) + ", add more.\n"
            "- Use data from the previous agents' research above. Do NOT fabricate hotel or attraction names.\n"
            "- Every recommendation must explain WHY it was chosen.\n"
            "- ALL text fields must be PLAIN TEXT ONLY. NEVER include HTML tags (<div>, </div>, <span>, <p>, <br>, <a>, <b>, <i>, or ANY other HTML/XML markup) in ANY field.\n"
            "- URL fields (maps_url, website_url) must contain ONLY valid http:// or https:// URLs, or be empty string. NEVER put HTML fragments like '</div>' in URL fields.\n"
            "- Output ONLY valid JSON. No markdown fences. No text before or after the JSON.\n"
            "- The JSON must parse with json.loads() without errors."
        ),
        expected_output=(
            f"A single valid JSON object containing ALL fields: trip_summary, destination_overview, "
            f"recommended_hotels, attractions, daily_plans (EXACTLY {num_days} entries), budget, ai_insights, transport_options, "
            "restaurants, packing_checklist, travel_tips, best_times, trip_score"
        ),
        agent=agent,
    )
