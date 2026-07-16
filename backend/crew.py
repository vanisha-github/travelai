import logging
from crewai import Crew, Process

from agents import (
    create_travel_planner_agent,
    create_hotel_agent,
    create_attraction_agent,
    create_weather_agent,
    create_budget_agent,
)
from tasks import (
    create_hotel_task,
    create_attraction_task,
    create_weather_task,
    create_budget_task,
    create_planning_task,
)
from utils import build_trip_context

logger = logging.getLogger(__name__)


def build_crew(trip_request):
    """Build and configure the CrewAI crew for trip planning.

    Workflow (sequential):
        1. Hotel Agent → researches accommodations
        2. Attraction Agent → plans activities
        3. Weather Agent → provides weather data
        4. Budget Agent → estimates costs
        5. Travel Planner Agent → compiles final itinerary

    All agents share context through task outputs.
    """
    context = build_trip_context(trip_request)

    hotel_agent = create_hotel_agent()
    attraction_agent = create_attraction_agent()
    weather_agent = create_weather_agent()
    budget_agent = create_budget_agent()
    planner_agent = create_travel_planner_agent()

    hotel_task = create_hotel_task(hotel_agent, context)
    attraction_task = create_attraction_task(attraction_agent, context)
    weather_task = create_weather_task(weather_agent, context)
    budget_task = create_budget_task(budget_agent, context)
    planning_task = create_planning_task(planner_agent, context)

    hotel_task.context = []
    attraction_task.context = [hotel_task]
    weather_task.context = [hotel_task, attraction_task]
    budget_task.context = [hotel_task, attraction_task, weather_task]
    planning_task.context = [hotel_task, attraction_task, weather_task, budget_task]

    crew = Crew(
        agents=[hotel_agent, attraction_agent, weather_agent, budget_agent, planner_agent],
        tasks=[hotel_task, attraction_task, weather_task, budget_task, planning_task],
        process=Process.sequential,
        verbose=True,
    )

    logger.info("Crew built with %d agents and %d tasks", len(crew.agents), len(crew.tasks))
    return crew, context
