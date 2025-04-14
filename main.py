
from langgraph.graph import StateGraph, END
from langchain_core.runnables import RunnableLambda
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI
import requests

llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0)

class State(dict):
    sport: str = ""
    location: str = ""
    sport_type: str = ""
    weather: str = ""
    confirmed_sport: bool = False
    confirmed_location: bool = False

def extract_sport(state):
    return state | {"sport": state['sport']}

def ask_sport_type(state):
    prompt = ChatPromptTemplate.from_template(
        """
        Classify whether the following sport is indoor or outdoor: {sport}.
        Respond with just one word: Indoor or Outdoor.
        """
    )
    chain = prompt | llm | StrOutputParser()
    sport_type = chain.invoke({"sport": state['sport']}).strip()
    return state | {"sport_type": sport_type}

def confirm_sport_type(state):
    # If confirmed_sport is already True, no need to ask again
    if state.get('confirmed_sport', False):
        return state  # No need to change anything, we proceed further

    print(f"I concluded that your supplied sport is {state['sport']} which is an {state['sport_type']} sport. Confirm? (yes/no)")
    confirmation = input().lower()

    if confirmation == "yes":
        # If confirmed, set confirmed_sport to True and proceed
        return state | {"confirmed_sport": True}
    else:
        # If not confirmed, update the sport type to the opposite type (from Indoor to Outdoor or vice versa)
        new_sport_type = "Outdoor" if state['sport_type'].lower() == "indoor" else "Indoor"
        print(f"Updating sport type to {new_sport_type}.")
        return state | {"sport_type": new_sport_type, "confirmed_sport": True}


def get_location(state):
    print("Please enter your current location (City name):")
    location = input()
    return state | {"location": location}

def confirm_location(state):
    # If confirmed_location is already True, no need to ask again
    if state.get('confirmed_location', False):
        return state  # No need to change anything, we proceed further
    
    print(f"I see that you are located in {state['location']}, confirm? (yes/no)")
    confirmation = input().lower()

    if confirmation == "yes":
        # If confirmed, set confirmed_location to True and proceed
        return state | {"confirmed_location": True}
    else:
        print("Please re-enter your location:")
        new_location = input()
        return state | {"location": new_location, "confirmed_location": True}


def get_weather(state):
    API_KEY = "fd218f8fefc14820f412e84dd5a3a1d3"
    location = state['location']
    try:
        response = requests.get(f"https://api.openweathermap.org/data/2.5/weather?q={location}&appid={API_KEY}&units=metric")
        data = response.json()
        if data.get("weather"):
            weather_description = data['weather'][0]['description']
            temperature = data['main']['temp']
            weather = f"{weather_description}, {temperature}°C"
        else:
            weather = "Unknown"
    except Exception as e:
        weather = "Unknown"
    return state | {"weather": weather}

def decide(state):
    if state['sport_type'].lower() == "indoor":
        decision = f"Yes, it's a good day to play {state['sport']} since it's an indoor sport."
    elif "rain" in state['weather'].lower():
        decision = f"No, it might not be a good day to play {state['sport']} due to the current weather: {state['weather']}."
    else:
        decision = f"Yes, the weather seems fine for {state['sport']}. Current weather: {state['weather']}."
    print(decision)
    return state

graph = StateGraph(State)
graph.add_node("extract_sport", RunnableLambda(extract_sport))
graph.add_node("ask_sport_type", RunnableLambda(ask_sport_type))
graph.add_node("confirm_sport_type", RunnableLambda(confirm_sport_type))
graph.add_node("get_location", RunnableLambda(get_location))
graph.add_node("confirm_location", RunnableLambda(confirm_location))
graph.add_node("get_weather", RunnableLambda(get_weather))
graph.add_node("decide", RunnableLambda(decide))

graph.set_entry_point("extract_sport")

graph.add_edge("extract_sport", "ask_sport_type")
graph.add_edge("ask_sport_type", "confirm_sport_type")
graph.add_conditional_edges("confirm_sport_type", lambda state: "ask_sport_type" if not state['confirmed_sport'] else "get_location")
graph.add_edge("get_location", "confirm_location")
graph.add_conditional_edges("confirm_location", lambda state: "get_location" if not state['confirmed_location'] else "get_weather")
graph.add_edge("get_weather", "decide")
graph.add_edge("decide", END)

runnable = graph.compile()

# Start the chatbot
print("Welcome! Ask me if it's a good day to play a sport.")
sport_input = input("Which sport do you want to play? ")
runnable.invoke({"sport": sport_input})


