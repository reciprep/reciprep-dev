import uuid
import traceback
from flask import Blueprint, request, make_response, jsonify, g
from flask_restful import Api, Resource, url_for, reqparse

from helpers import recipe_to_json, json_to_recipe

from api import bcrypt, db
from api.models.user import User
from api.models.recipe import Recipe
from api.models.ingredient import Ingredient, RecipeIngredient, PantryIngredient
from api.decorators import is_logged_in

recipe_blueprint = Blueprint('recipe', __name__)
recipe_api = Api(recipe_blueprint)

class SearchResource(Resource):
    """
    Recipe search resource
    """

    decorators = [is_logged_in]

    def get(self):
        """
        Search for ingredients that match the user's criteria and pantry contents

        This method is hacked together and should be completely rewritten.
            Not kidding, it's awful.
                Seriously.
        """

        query = request.args.get('query')
        filter_ = request.args.get('filter')
        if filter_ == 'true':
            if query is not None:
                recipes = Recipe.query.search(query.replace('+', ' ')).all()
            else:
                recipes = Recipe.query.all()

            responseObject = {
                'status': 'success',
                'data': {
                    'recipes': [recipe_to_json(r, make_json=False, verbose=False) for r in recipes]
                }
            }

            return make_response(jsonify(responseObject), 200)



        user = User.query.get(g.user_id)
        result = PantryIngredient.query.filter(PantryIngredient.user_id == user.id).all()

        ingredients = {}
        for i in result:
            ingredients[i.ingredient_id.hex] = i.value

        result = RecipeIngredient.query.filter(
            (RecipeIngredient.ingredient_id.in_(ingredients.keys()))
        )\
        .all()

        result = [i for i in result if i.value <= ingredients[i.ingredient_id.hex]]

        matches = {}
        expected = {}

        for i in result:
            if i.recipe_id.hex in matches:
                matches[i.recipe_id.hex] += 1
            else:
                expected[i.recipe_id.hex] = len(RecipeIngredient.query.filter(RecipeIngredient.recipe_id == i.recipe_id.hex).all())
                matches[i.recipe_id.hex] = 1

        recipe_ids = []

        for key in matches:
            if expected[key] <= matches[key]:
                recipe_ids.append(key)

        if query is not None:
            recipes = Recipe.query \
                .filter(Recipe.id.in_(recipe_ids)) \
                .search(query.replace('+', ' ')) \
                .all()
        else:
            recipes = Recipe.query.filter(Recipe.id.in_(recipe_ids)).all()

        [recipe_to_json(r, make_json=False, verbose=False) for r in recipes]

        responseObject = {
            'status': 'success',
            'data': {
                'recipes': [recipe_to_json(r, make_json=False, verbose=False) for r in recipes]
            }
        }

        return make_response(jsonify(responseObject), 200)

class RateResource(Resource):
    """
    Recipe rating resource
    """

    decorators = [is_logged_in]

    def patch(self, recipe_id):

        pass


class CreateResource(Resource):
    """
    Recipe creation resource
    """

    decorators = [is_logged_in]

    def post(self):
        try:
            post_data = request.get_json()
            if 'rating' in post_data:
                post_data['rating'] = None

            recipe = Recipe.query.filter(Recipe.name == post_data['name']).first()

            if not recipe:
                recipe = json_to_recipe(post_data, creator=g.user)
                db.session.commit()

                responseObject = {
                    'status': 'success',
                    'recipe_id': recipe.id.hex
                }

                return make_response(jsonify(responseObject), 200)
            else:
                responseObject = {
                    'status': 'fail',
                    'message': 'Recipe with name %s already exists.' % recipe.name
                }
                return make_response(jsonify(responseObject), 202)

        except KeyError:
            responseObject = {
                'status': 'fail',
                'message': 'Invalid recipe information provided.'
            }

            return make_response(jsonify(responseObject), 400)
        except Exception as e:
            traceback.print_exc()
            print(e)

class PrepareResource(Resource):
    """
    Preparing a recipe deducts its ingredients from the User's pantry
    """

    decorators = [is_logged_in]

    def get(self, recipe_id):
        pass


class ModifyResource(Resource):
    """
    Recipe modification resource
    """
    decorators = [is_logged_in]

    def patch(self, recipe_id):
        pass

    def delete(self, recipe_id):
        pass

class DetailsResource(Resource):
    """
    Recipe details resource
    """
    def get(self, recipe_id):
        try:
            uuid.UUID(hex=recipe_id)
            recipe = Recipe.query.get(recipe_id)

            if recipe:
                responseObject = {
                    'status': 'success',
                    'data': recipe_to_json(recipe, make_json=False)
                }
                return make_response(jsonify(responseObject), 200)

            else:
                responseObject = {
                    'status': 'fail',
                    'message': 'Recipe %s not found.' % recipe_id
                }
                return make_response(jsonify(responseObject), 404)

        except ValueError:
            responseObject = {
                'status': 'fail',
                'message': '%s is not a valid recipe id.' % recipe_id
            }
            return make_response(jsonify(responseObject), 400)


recipe_api.add_resource(SearchResource, '/api/recipe/search')
recipe_api.add_resource(CreateResource, '/api/recipe')
recipe_api.add_resource(ModifyResource, '/api/recipe/<string:recipe_id>')
recipe_api.add_resource(DetailsResource, '/api/recipe/<string:recipe_id>')
recipe_api.add_resource(RateResource, '/api/recipe/<string:recipe_id>/rate')
recipe_api.add_resource(PrepareResource, '/api/recipe/<string:recipe_id>/prepare')
