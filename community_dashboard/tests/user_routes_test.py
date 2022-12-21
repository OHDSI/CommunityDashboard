import pytest
from datetime import datetime, date
from numpy import double
from community_dashboard import app
from community_dashboard.handlers import user_routes, pubmed_miner, youtube_miner, ehden_miner
from community_dashboard.config import Keys
from flask import Flask, jsonify, render_template, request
import json
from azure.cosmos import CosmosClient, PartitionKey

def test_numberFormatter():
    # Test with a number greater than 999999
    assert user_routes.numberFormatter(100000000) == '100M'
    # Test with a number greater than 9999
    assert user_routes.numberFormatter(10000) == '10K'
    # Test with a number greater than 999
    assert user_routes.numberFormatter(1000) == '1,000'
    # Test with a number less than 1000
    assert user_routes.numberFormatter(100) == 100

def test_init_cosmos():
    # Test creating a new container
    container = user_routes.init_cosmos('test_container')
    assert container is not None

# todo: add test coverage to index(), that will require flask app running
# and connect to Azure.