from crewai import Task


def create_hotel_task(agent, trip_context: str) -> Task:
    """Task for the Hotel Agent to research and recommend accommodations."""
    return Task(
        description=(
            f"Based on the following trip details:\n{trip_context}\n\n"
            "Research and recommend hotels for this trip. For each hotel, provide:\n"
            "- Hotel name\n"
            "- Rating (out of 5)\n"
            "- Approximate price per night in USD\n"
            "- Location and proximity to attractions\n"
            "- Why this hotel is recommended for this traveller\n\n"
            "Provide 2-3 hotel options at different price points. "
            "Search the web for current hotel information and prices."
        ),
        expected_output=(
            "A structured list of 2-3 hotel recommendations with name, rating, "
            "price per night, location, and recommendation reason for each."
        ),
        agent=agent,
    )


def create_attraction_task(agent, trip_context: str) -> Task:
    """Task for the Attraction Agent to find and plan sightseeing activities."""
    return Task(
        description=(
            f"Based on the following trip details:\n{trip_context}\n\n"
            "Research and plan attractions and activities for each day of the trip. For each day, provide:\n"
            "- Morning activity with brief description\n"
            "- Afternoon activity with brief description\n"
            "- Evening activity with brief description\n"
            "- Why each activity is worth the time\n\n"
            "Consider the traveller's interests and create a logical visiting order. "
            "Search the web for current attraction information."
        ),
        expected_output=(
            "A day-by-day plan of attractions and activities with morning, afternoon, "
            "and evening breakdowns, including descriptions and reasons for each."
        ),
        agent=agent,
    )


def create_weather_task(agent, trip_context: str) -> Task:
    """Task for the Weather Agent to provide climate information."""
    return Task(
        description=(
            f"Based on the following trip details:\n{trip_context}\n\n"
            "Research the current and expected weather conditions for the destination. Provide:\n"
            "- Current temperature and conditions\n"
            "- Humidity level\n"
            "- Weather forecast for the trip duration\n"
            "- Clothing recommendations\n"
            "- Whether to plan more indoor or outdoor activities\n"
            "- Any weather-related travel tips\n\n"
            "Search the web for current weather information."
        ),
        expected_output=(
            "Weather summary including temperature, humidity, conditions, "
            "clothing suggestions, and indoor/outdoor activity recommendations."
        ),
        agent=agent,
    )


def create_budget_task(agent, trip_context: str) -> Task:
    """Task for the Budget Agent to estimate trip costs."""
    return Task(
        description=(
            f"Based on the following trip details:\n{trip_context}\n\n"
            "Estimate the total trip cost broken down into these categories:\n"
            "- Hotel (total for all nights)\n"
            "- Food (daily meals estimate)\n"
            "- Transport (local transport, airport transfers)\n"
            "- Activities (attraction tickets, tours)\n"
            "- Miscellaneous (shopping, tips, emergencies)\n\n"
            "Calculate the total estimated cost and compare against the user's budget.\n"
            "If the estimate exceeds the budget, provide specific cost-saving suggestions.\n"
            "Search the web for current prices and cost of living information."
        ),
        expected_output=(
            "A detailed budget breakdown with hotel, food, transport, activities, "
            "and miscellaneous costs, total estimate, budget comparison, and "
            "cost-saving suggestions if needed."
        ),
        agent=agent,
    )


def create_planning_task(agent, trip_context: str) -> Task:
    """Task for the Travel Planner Agent to compile the final itinerary."""
    return Task(
        description=(
            f"Based on the following trip details:\n{trip_context}\n\n"
            "You have received research from specialized agents covering:\n"
            "- Hotel recommendations\n"
            "- Attraction and activity plans\n"
            "- Weather conditions and advice\n"
            "- Budget estimates\n\n"
            "Now compile all this information into a comprehensive, final travel itinerary. "
            "Structure the output as follows:\n\n"
            "1. TRIP SUMMARY - Brief overview of the trip\n"
            "2. DESTINATION OVERVIEW - Key facts about the destination\n"
            "3. WEATHER SUMMARY - Temperature, humidity, condition, and AI suggestions\n"
            "4. RECOMMENDED HOTELS - List hotels with name, rating, price, location, reason\n"
            "5. ESTIMATED BUDGET - Full breakdown with categories and total\n"
            "6. DAY-BY-DAY ITINERARY - For each day: morning, afternoon, evening, daily cost\n"
            "7. TRAVEL TIPS - Practical tips for the trip\n"
            "8. THINGS TO CARRY - Packing checklist\n"
            "9. BEST TIMES TO VISIT ATTRACTIONS\n\n"
            "Format everything cleanly and make it easy to read. "
            "Use the information from the other agents, do not fabricate data."
        ),
        expected_output=(
            "A complete, well-structured travel itinerary in markdown format containing "
            "all sections: trip summary, destination overview, weather, hotels, budget, "
            "day-by-day plans, travel tips, packing list, and best visiting times."
        ),
        agent=agent,
    )
