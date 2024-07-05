"""
In this example, we:
1. Connect to the local nillion-devnet
2. Store the secure similarity program
3. Store secrets (ratings) to be used in the computation
4. Compute the secure similarity program with stored secrets and another computation time secret
"""

import asyncio
import py_nillion_client as nillion
import os

from py_nillion_client import NodeKey, UserKey
from dotenv import load_dotenv
from nillion_python_helpers import get_quote_and_pay, create_nillion_client, create_payments_config

from cosmpy.aerial.client import LedgerClient
from cosmpy.aerial.wallet import LocalWallet
from cosmpy.crypto.keypairs import PrivateKey

home = os.getenv("HOME")
load_dotenv(f"{home}/.config/nillion/nillion-devnet.env")

def get_program_path(program_name):
    # Get the absolute path of the compiled program
    base_dir = os.path.abspath(os.path.dirname(__file__))
    program_path = os.path.join(base_dir, f"../nada_quickstart_programs/target/{program_name}.nada.bin")
    if not os.path.isfile(program_path):
        raise ValueError(f"Program not found at {program_path}")
    return program_path

async def main():
    # 1. Initial setup
    # 1.1. Get cluster_id, grpc_endpoint, & chain_id from the .env file
    cluster_id = os.getenv("NILLION_CLUSTER_ID")
    grpc_endpoint = os.getenv("NILLION_NILCHAIN_GRPC")
    chain_id = os.getenv("NILLION_NILCHAIN_CHAIN_ID")
    # 1.2 pick a seed and generate user and node keys
    seed = "my_seed"
    userkey = UserKey.from_seed(seed)
    nodekey = NodeKey.from_seed(seed)

    # 2. Initialize NillionClient against nillion-devnet
    # Create Nillion Client for user
    client = create_nillion_client(userkey, nodekey)

    party_id = client.party_id
    user_id = client.user_id

    # 3. Pay for and store the program
    # Set the program name and path to the compiled program
    program_name = "main"
    program_mir_path = get_program_path(program_name)

    # Create payments config, client and wallet
    payments_config = create_payments_config(chain_id, grpc_endpoint)
    payments_client = LedgerClient(payments_config)
    payments_wallet = LocalWallet(
        PrivateKey(bytes.fromhex(os.getenv("NILLION_NILCHAIN_PRIVATE_KEY_0"))),
        prefix="nillion",
    )

    # Pay to store the program and obtain a receipt of the payment
    receipt_store_program = await get_quote_and_pay(
        client,
        nillion.Operation.store_program(program_mir_path),
        payments_wallet,
        payments_client,
        cluster_id,
    )

    # Store the program
    action_id = await client.store_program(
        cluster_id, program_name, program_mir_path, receipt_store_program
    )

    # Create a variable for the program_id, which is the {user_id}/{program_name}. We will need this later
    program_id = f"{user_id}/{program_name}"
    print("Stored program. action_id:", action_id)
    print("Stored program_id:", program_id)

    # 4. Create the 1st secret, add permissions, pay for and store it in the network
    # Create a secret named "Rating1" and "Rating2" with any value, ex: 5 and 7
    rating_secret = nillion.NadaValues(
        {
            "Rating1": nillion.SecretInteger(5),
            "Rating2": nillion.SecretInteger(7),
        }
    )

    # Set the input party for the secret
    # The party name needs to match the party name that is storing "Rating1" and "Rating2" in the program
    party1_name = "Party1"

    # Set permissions for the client to compute on the program
    permissions = nillion.Permissions.default_for_user(client.user_id)
    permissions.add_compute_permissions({client.user_id: {program_id}})

    # Pay for and store the secret in the network and print the returned store_id
    receipt_store = await get_quote_and_pay(
        client,
        nillion.Operation.store_values(rating_secret, ttl_days=5),
        payments_wallet,
        payments_client,
        cluster_id,
    )
    # Store a secret
    store_id = await client.store_values(
        cluster_id, rating_secret, permissions, receipt_store
    )
    
    print(f"Computing using program {program_id}")
    print(f"Use secret store_id: {store_id}")

    # Add the required inputs from the CentralServer
    central_server_inputs = nillion.NadaValues(
        {
            "ConstantZero": nillion.SecretInteger(1),
            "MovieRating_MovieA": nillion.SecretInteger(8),
            "MovieRating_MovieB": nillion.SecretInteger(6),
            "MovieRating_MovieC": nillion.SecretInteger(7),
        }
    )

    # Set permissions for the client to compute on the program
    permissions_central_server = nillion.Permissions.default_for_user(client.user_id)
    permissions_central_server.add_compute_permissions({client.user_id: {program_id}})

    # Pay for and store the central server inputs in the network and print the returned store_id
    receipt_store_central_server = await get_quote_and_pay(
        client,
        nillion.Operation.store_values(central_server_inputs, ttl_days=5),
        payments_wallet,
        payments_client,
        cluster_id,
    )
    store_id_central_server = await client.store_values(
        cluster_id, central_server_inputs, permissions_central_server, receipt_store_central_server
    )
    print(f"Stored central server inputs. Store ID: {store_id_central_server}")

    # 5. Create compute bindings to set input and output parties and pay for & run the computation
    compute_bindings = nillion.ProgramBindings(program_id)
    compute_bindings.add_input_party(party1_name, party_id)
    compute_bindings.add_input_party("CentralServer", party_id)  # Ensure CentralServer is bound as an input party
    compute_bindings.add_output_party("CentralServer", party_id)  # Ensure CentralServer is bound as an output party

    # Pay for the compute
    receipt_compute = await get_quote_and_pay(
        client,
        nillion.Operation.compute(program_id, nillion.NadaValues({})),  # Provide an empty values argument
        payments_wallet,
        payments_client,
        cluster_id,
    )

    # Compute on the secret
    compute_id = await client.compute(
        cluster_id,
        compute_bindings,
        [store_id, store_id_central_server],
        nillion.NadaValues({}),  # No additional computation time secrets
        receipt_compute,
    )

    # 8. Return the computation result
    print(f"The computation was sent to the network. compute_id: {compute_id}")
    while True:
        compute_event = await client.next_compute_event()
        if isinstance(compute_event, nillion.ComputeFinishedEvent):
            print(f"✅  Compute complete for compute_id {compute_event.uuid}")
            print(f"🖥️  The result is {compute_event.result.value}")
            return compute_event.result.value


if __name__ == "__main__":
    asyncio.run(main())
