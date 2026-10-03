import logging
import sys
import requests
from mcp.server.fastmcp import FastMCP

logger = logging.getLogger("meals_server")
mcp = FastMCP("meals")

# turns one full meal object to meal_details shape
def format_meal_details(meal):
    ingredients = []
    for n in range(1, 21):
        name = meal.get("strIngredient" + str(n))
        measure = meal.get("strMeasure" + str(n))
        if name and name.strip():
            ingredients.append({"name": name.strip(), "measure": (measure or "").strip()})
    return {
        "id": meal.get("idMeal"),
        "name": meal.get("strMeal"),
        "category": meal.get("strCategory"),
        "area": meal.get("strArea"),
        "instructions": meal.get("strInstructions"),
        "image": meal.get("strMealThumb"),
        "source": meal.get("strSource"),
        "youtube": meal.get("strYoutube"),
        "ingredients": ingredients,
    }

@mcp.tool()
def search_meals_by_name(query: str, limit: int = 5) -> list:
    try:
        response = requests.get("https://www.themealdb.com/api/json/v1/1/search.php?s=" + query, timeout=10)
        response.raise_for_status()
        data= response.json()
    except requests.exceptions.RequestException as e:
        logger.error("MealDB request failed: %s", e)
        raise RuntimeError("Cannot reach MealDB: " + str(e))
    except ValueError as e:
        logger.error("MealDB returned bad JSON: %s", e)
        raise RuntimeError("MealDB returned unreadable response")
    meals = data.get("meals")
    if not meals:
        logger.info("no matches for query: %s", query)
        return [] #for empty result
    results = []
    for meal in meals[:limit]:
        results. append({
            "id": meal.get("idMeal"),
            "name": meal.get("strMeal"),
            "area": meal.get("strArea"),
            "category": meal.get("strCategory"),
            "thumb": meal.get("strMealThumb")
        })
    return results

@mcp. tool()
def meals_by_ingredient(ingredient: str, limit: int = 12) -> list:
    try:
        response = requests.get("https://www.themealdb.com/api/json/v1/1/filter.php?i=" + ingredient, timeout=10)
        response.raise_for_status()
        data= response.json()
    except requests.exceptions.RequestException as e:
        logger.error("MealDB request failed: %s", e)
        raise RuntimeError("Cannot reach MealDB: " + str(e))
    except ValueError as e:
        logger.error("MealDB returned bad JSON: %s", e)
        raise RuntimeError("MealDB returned unreadable response")
    meals = data.get("meals")
    if not meals:
        logger.info("no matches for ingredient: %s", ingredient)
        return []
    results = []
    for meal in meals[:limit]:
        results. append({
        "id": meal.get("idMeal"),
        "name": meal.get("strMeal"),
        "thumb": meal.get("strMealThumb"),
        })
    return results

@mcp.tool()
def random_meal() -> dict:
    try:
        response = requests.get("https://www.themealdb.com/api/json/v1/1/random.php", timeout=10)
        response.raise_for_status()
        data= response.json()
    except requests.exceptions.RequestException as e:
        logger.error("MealDB request failed: %s", e)
        raise RuntimeError("Cannot reach MealDB: " + str(e))
    except ValueError as e:
        logger.error("MealDB returned bad JSON: %s", e)
        raise RuntimeError("MealDB returned unreadable response")
    meals = data.get("meals")
    if not meals:
        return {"message": "no matches"}
    return format_meal_details(meals[0])

@mcp.tool()
def meal_details(id: str) -> dict:
    try:
        response = requests.get("https://www.themealdb.com/api/json/v1/1/lookup.php?i=" + str(id), timeout=10)
        response.raise_for_status()
        data= response.json()
    except requests.exceptions.RequestException as e:
        logger.error("MealDB request failed: %s", e)
        raise RuntimeError("Cannot reach MealDB: " + str(e))
    except ValueError as e:
        logger.error("MealDB returned bad JSON: %s", e)
        raise RuntimeError("MealDB returned unreadable response")
    meals = data.get("meals")
    if not meals:
        logger.info("no match for id: %s", id)
        return {"message": "no matches"}
    return format_meal_details (meals [0])

if __name__ =="__main__":
    mcp.run(transport="stdio")


    