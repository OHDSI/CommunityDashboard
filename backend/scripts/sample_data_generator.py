#!/usr/bin/env python3
"""
Sample data generator for OHDSI Community Intelligence Platform.
Generates realistic OHDSI content including articles, videos, repositories, and datasets.
"""

import json
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any
from uuid import uuid4
import logging

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from faker import Faker
from app.database import es_client
from app.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

fake = Faker()

# OHDSI-specific terms and topics
OHDSI_TOPICS = [
    "OMOP CDM", "Atlas", "HADES", "Achilles", "DataQualityDashboard",
    "WebAPI", "Athena", "OHDSI Forums", "StudyProtocols", "PhenotypeLibrary",
    "CohortDiagnostics", "PatientLevelPrediction", "CohortMethod",
    "EvidenceSynthesis", "ClinicalCharacterization"
]

OHDSI_CATEGORIES = [
    "Observational data standards and management",
    "Methodological research",
    "Open-source analytics development",
    "Clinical applications"
]

AUTHORS = [
    {"name": "Patrick Ryan", "email": "pryan@ohdsi.org", "affiliation": "Janssen R&D"},
    {"name": "George Hripcsak", "email": "ghripcsak@columbia.edu", "affiliation": "Columbia University"},
    {"name": "Marc Suchard", "email": "msuchard@ucla.edu", "affiliation": "UCLA"},
    {"name": "Martijn Schuemie", "email": "schuemie@ohdsi.org", "affiliation": "Janssen R&D"},
    {"name": "Christian Reich", "email": "reich@ohdsi.org", "affiliation": "IQVIA"},
    {"name": "Jon Duke", "email": "jduke@gatech.edu", "affiliation": "Georgia Tech"},
    {"name": "Peter Rijnbeek", "email": "p.rijnbeek@erasmusmc.nl", "affiliation": "Erasmus MC"},
    {"name": "David Madigan", "email": "dmadigan@columbia.edu", "affiliation": "Northeastern University"},
    {"name": "Seng Chan You", "email": "seng.chan.you@gmail.com", "affiliation": "Yonsei University"},
    {"name": "Jenna Reps", "email": "jreps@ohdsi.org", "affiliation": "Janssen R&D"}
]

def generate_article() -> Dict[str, Any]:
    """Generate a sample research article."""
    ml_score = random.uniform(0.3, 1.0)
    
    # Determine approval status based on ML score
    if ml_score >= 0.85:
        approval_status = "approved"
    elif ml_score >= 0.6:
        approval_status = "pending"
    else:
        approval_status = "rejected"
    
    # Generate 1-5 authors
    num_authors = random.randint(1, 5)
    article_authors = random.sample(AUTHORS, min(num_authors, len(AUTHORS)))
    
    # Select 1-3 categories
    categories = random.sample(OHDSI_CATEGORIES, random.randint(1, 3))
    
    title_parts = [
        random.choice(["Evaluating", "Assessing", "Analyzing", "Characterizing", "Investigating"]),
        random.choice(OHDSI_TOPICS),
        random.choice(["in Real-World Data", "Using OMOP CDM", "Across the OHDSI Network", 
                      "for Drug Safety", "in Electronic Health Records"])
    ]
    
    return {
        "id": str(uuid4()),
        "title": " ".join(title_parts),
        "abstract": fake.text(max_nb_chars=500),
        "content": fake.text(max_nb_chars=2000),
        "content_type": "article",
        "authors": article_authors,
        "published_date": fake.date_time_between(start_date="-2y", end_date="now").isoformat(),
        "ml_score": round(ml_score, 3),
        "ohdsi_categories": categories,
        "predicted_categories": categories if ml_score > 0.7 else random.sample(categories, 1),
        "approval_status": approval_status,
        "url": f"https://pubmed.ncbi.nlm.nih.gov/{fake.random_int(min=30000000, max=35000000)}/",
        "metrics": {
            "view_count": fake.random_int(min=0, max=1000),
            "bookmark_count": fake.random_int(min=0, max=50),
            "share_count": fake.random_int(min=0, max=25)
        },
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }

def generate_video() -> Dict[str, Any]:
    """Generate a sample video content."""
    ml_score = random.uniform(0.5, 1.0)
    
    if ml_score >= 0.8:
        approval_status = "approved"
    elif ml_score >= 0.65:
        approval_status = "pending"
    else:
        approval_status = "rejected"
    
    video_types = ["Tutorial", "Webinar", "Conference Talk", "Workshop", "Demo"]
    
    return {
        "id": str(uuid4()),
        "title": f"{random.choice(video_types)}: {random.choice(OHDSI_TOPICS)}",
        "abstract": fake.text(max_nb_chars=200),
        "content": fake.text(max_nb_chars=500),
        "content_type": "video",
        "authors": random.sample(AUTHORS, random.randint(1, 2)),
        "published_date": fake.date_time_between(start_date="-1y", end_date="now").isoformat(),
        "ml_score": round(ml_score, 3),
        "ohdsi_categories": random.sample(OHDSI_CATEGORIES, random.randint(1, 2)),
        "predicted_categories": random.sample(OHDSI_CATEGORIES, 1),
        "approval_status": approval_status,
        "url": f"https://youtube.com/watch?v={fake.uuid4()[:11]}",
        "duration_minutes": fake.random_int(min=5, max=120),
        "metrics": {
            "view_count": fake.random_int(min=0, max=5000),
            "bookmark_count": fake.random_int(min=0, max=100),
            "share_count": fake.random_int(min=0, max=50)
        },
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }

def generate_repository() -> Dict[str, Any]:
    """Generate a sample GitHub repository."""
    ml_score = random.uniform(0.6, 1.0)
    
    if ml_score >= 0.75:
        approval_status = "approved"
    else:
        approval_status = "pending"
    
    repo_names = [
        "PhenotypeAlgorithm", "StudyProtocol", "ShinyApp", "RPackage",
        "PredictionModel", "CohortDefinition", "DataQualityCheck"
    ]
    
    return {
        "id": str(uuid4()),
        "title": f"{random.choice(repo_names)}-{random.choice(OHDSI_TOPICS).replace(' ', '')}",
        "abstract": fake.text(max_nb_chars=300),
        "content": fake.text(max_nb_chars=1000),
        "content_type": "repository",
        "authors": random.sample(AUTHORS, random.randint(1, 3)),
        "published_date": fake.date_time_between(start_date="-2y", end_date="now").isoformat(),
        "ml_score": round(ml_score, 3),
        "ohdsi_categories": random.sample(OHDSI_CATEGORIES, random.randint(1, 3)),
        "predicted_categories": random.sample(OHDSI_CATEGORIES, 2),
        "approval_status": approval_status,
        "url": f"https://github.com/OHDSI/{fake.slug()}",
        "stars": fake.random_int(min=0, max=500),
        "forks": fake.random_int(min=0, max=100),
        "language": random.choice(["R", "Python", "SQL", "JavaScript"]),
        "metrics": {
            "view_count": fake.random_int(min=0, max=2000),
            "bookmark_count": fake.random_int(min=0, max=75),
            "share_count": fake.random_int(min=0, max=30)
        },
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }

def generate_dataset() -> Dict[str, Any]:
    """Generate a sample dataset."""
    ml_score = random.uniform(0.7, 1.0)
    approval_status = "approved" if ml_score >= 0.8 else "pending"
    
    dataset_types = [
        "Synthetic Data", "Benchmark Dataset", "Gold Standard",
        "Reference Set", "Test Cases", "Validation Cohort"
    ]
    
    return {
        "id": str(uuid4()),
        "title": f"{random.choice(dataset_types)} for {random.choice(OHDSI_TOPICS)}",
        "abstract": fake.text(max_nb_chars=250),
        "content": fake.text(max_nb_chars=800),
        "content_type": "dataset",
        "authors": random.sample(AUTHORS, random.randint(1, 4)),
        "published_date": fake.date_time_between(start_date="-1y", end_date="now").isoformat(),
        "ml_score": round(ml_score, 3),
        "ohdsi_categories": random.sample(OHDSI_CATEGORIES, random.randint(1, 2)),
        "predicted_categories": random.sample(OHDSI_CATEGORIES, 1),
        "approval_status": approval_status,
        "url": f"https://data.ohdsi.org/{fake.slug()}",
        "size_mb": fake.random_int(min=1, max=10000),
        "record_count": fake.random_int(min=100, max=1000000),
        "metrics": {
            "view_count": fake.random_int(min=0, max=500),
            "bookmark_count": fake.random_int(min=0, max=25),
            "share_count": fake.random_int(min=0, max=10)
        },
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }

def load_sample_data():
    """Load sample data into Elasticsearch."""
    logger.info("Generating sample data...")
    
    # Generate content
    content_items = []
    
    # Generate articles (60% of content)
    for _ in range(60):
        content_items.append(generate_article())
    
    # Generate videos (20% of content)
    for _ in range(20):
        content_items.append(generate_video())
    
    # Generate repositories (10% of content)
    for _ in range(10):
        content_items.append(generate_repository())
    
    # Generate datasets (10% of content)
    for _ in range(10):
        content_items.append(generate_dataset())
    
    logger.info(f"Generated {len(content_items)} content items")
    
    # Load data into appropriate indices
    approved_count = 0
    pending_count = 0
    rejected_count = 0
    
    for item in content_items:
        if item["approval_status"] == "approved":
            index = settings.content_index
            approved_count += 1
        elif item["approval_status"] == "pending":
            index = settings.review_index
            pending_count += 1
        else:
            index = settings.review_index  # Rejected items stay in review queue
            rejected_count += 1
        
        try:
            es_client.index(index=index, id=item["id"], body=item)
        except Exception as e:
            logger.error(f"Error indexing item {item['id']}: {e}")
    
    logger.info(f"\nData loading complete:")
    logger.info(f"  - Approved: {approved_count} items")
    logger.info(f"  - Pending review: {pending_count} items")
    logger.info(f"  - Rejected: {rejected_count} items")
    
    # Refresh indices to make data searchable immediately
    es_client.indices.refresh(index=f"{settings.content_index},{settings.review_index}")
    logger.info("Indices refreshed - data is now searchable")

if __name__ == "__main__":
    load_sample_data()
    print("\nSample data loaded successfully!")
    print("You can now:")
    print("  - Search content at http://localhost:3000")
    print("  - Review pending items at http://localhost:3000/review")
    print("  - Access GraphQL at http://localhost:8000/graphql")