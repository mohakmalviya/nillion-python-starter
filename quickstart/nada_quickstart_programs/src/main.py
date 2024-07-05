from nada_dsl import *

def nada_main():
    party1 = Party(name="Party1")
    central_server = Party(name="CentralServer")

    rating1 = SecretInteger(Input(name="Rating1", party=party1))
    rating2 = SecretInteger(Input(name="Rating2", party=party1))

    movies = ["MovieA", "MovieB", "MovieC"]

    @nada_fn
    def add(a: SecretInteger, b: SecretInteger) -> SecretInteger:
        return a + b

    @nada_fn
    def multiply(a: SecretInteger, b: SecretInteger) -> SecretInteger:
        return a * b

    @nada_fn
    def subtract(a: SecretInteger, b: SecretInteger) -> SecretInteger:
        return a - b

    @nada_fn
    def square(a: SecretInteger) -> SecretInteger:
        return a * a

    @nada_fn
    def secure_similarity(rating1: SecretInteger, rating2: SecretInteger) -> SecretInteger:
        difference = subtract(rating1, rating2)
        squared_difference = square(difference)
        return SecretInteger(Input(name="ConstantZero", party=central_server)) - squared_difference

    similarities = [
        secure_similarity(rating2, SecretInteger(Input(name=f"MovieRating_{movie}", party=central_server)))
        for movie in movies
    ]

    output_similarities = [Output(sim, f"Similarity_{i}", central_server) for i, sim in enumerate(similarities)]

    return output_similarities
