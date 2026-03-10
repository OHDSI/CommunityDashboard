#!/usr/bin/env python3
"""Load sample data into Elasticsearch for testing"""

import sys
import os
import random
from pathlib import Path
from datetime import datetime, timedelta
from faker import Faker
import json

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from elasticsearch import Elasticsearch
from app.config import settings

fake = Faker()

# OHDSI-specific content categories
OHDSI_CATEGORIES = [
    "OMOP CDM", "Atlas", "HADES", "Achilles", "WebAPI",
    "Data Quality", "Phenotyping", "Patient-Level Prediction",
    "Population-Level Estimation", "Characterization",
    "ETL", "Vocabulary", "OHDSI Studies", "Methods Library",
    "R Packages", "SQL", "Community Tools"
]

# Content types
CONTENT_TYPES = ["article", "video", "github", "dataset", "presentation"]

# Sample titles related to OHDSI
TITLE_TEMPLATES = [
    "Implementing OMOP CDM v{} in {}",
    "Best Practices for {} Using Atlas",
    "Data Quality Assessment with {}",
    "Building {} Cohorts in OHDSI",
    "Phenotype Development for {}",
    "ETL Strategies for {} Data Sources",
    "{} Analysis Using HADES",
    "Vocabulary Mapping for {}",
    "Patient-Level Prediction Models for {}",
    "Network Study: {} Across Multiple Databases"
]

# Medical conditions and topics
MEDICAL_TOPICS = [
    "COVID-19", "Diabetes", "Hypertension", "Cancer", "Cardiovascular Disease",
    "Mental Health", "Rare Diseases", "Drug Safety", "Vaccine Effectiveness",
    "Chronic Pain", "Respiratory Diseases", "Neurological Disorders"
]

def generate_sample_content(num_items=100):
    """Generate sample OHDSI content"""
    items = []
    
    for i in range(num_items):
        # Generate realistic OHDSI content
        topic = random.choice(MEDICAL_TOPICS)
        template = random.choice(TITLE_TEMPLATES)
        
        if "{}" in template:
            if template.startswith("Implementing"):
                title = template.format(random.choice(["5.3", "5.4", "6.0"]), topic)
            else:
                title = template.format(topic)
        else:
            title = template
        
        # Generate authors
        num_authors = random.randint(1, 5)
        authors = []
        for _ in range(num_authors):
            authors.append({
                "name": fake.name(),
                "email": fake.email(),
                "affiliation": fake.company()
            })
        
        # Generate content
        content_type = random.choice(CONTENT_TYPES)
        
        # Set URL based on content type
        if content_type == "github":
            url = f"https://github.com/OHDSI/{fake.word()}"
        elif content_type == "video":
            url = f"https://youtube.com/watch?v={fake.uuid4()[:11]}"
        else:
            url = fake.url()
        
        # Generate abstract
        abstract = f"This study explores {topic} using OHDSI tools and methods. "
        abstract += fake.text(max_nb_chars=300)
        
        # Generate dates
        published_date = fake.date_time_between(
            start_date="-1 year",
            end_date="now"
        )
        
        # ML score (higher for more recent and certain categories)
        base_score = random.uniform(0.4, 0.95)
        if "OMOP CDM" in title or "Atlas" in title:
            base_score += 0.1
        ml_score = min(base_score, 1.0)
        
        # Categories (1-3 categories per item)
        num_categories = random.randint(1, 3)
        categories = random.sample(OHDSI_CATEGORIES, num_categories)
        
        # Metrics
        days_old = (datetime.now() - published_date).days
        view_count = random.randint(0, max(1, 1000 - days_old * 2))
        bookmark_count = random.randint(0, max(0, view_count // 10))
        
        item = {
            "title": title,
            "abstract": abstract,
            "content": fake.text(max_nb_chars=2000),
            "url": url,
            "content_type": content_type,
            "authors": authors,
            "published_date": published_date.isoformat(),
            "ml_score": ml_score,
            "ohdsi_categories": categories,
            "view_count": view_count,
            "bookmark_count": bookmark_count,
            "references": [fake.uuid4() for _ in range(random.randint(0, 5))],
            "cited_by": [fake.uuid4() for _ in range(random.randint(0, 3))],
            "created_at": published_date.isoformat(),
            "updated_at": datetime.now().isoformat(),
            "suggest": {"input": title}
        }
        
        # Determine approval status
        if ml_score > 0.8:
            item["approval_status"] = "approved"
        elif ml_score > 0.6:
            item["approval_status"] = random.choice(["approved", "pending"])
        else:
            item["approval_status"] = random.choice(["pending", "rejected"])
        
        items.append(item)
    
    return items

def generate_review_items(num_items=20):
    """Generate items for review queue"""
    items = []
    
    for i in range(num_items):
        topic = random.choice(MEDICAL_TOPICS)
        template = random.choice(TITLE_TEMPLATES)
        
        if "{}" in template:
            title = template.format(topic) if not template.startswith("Implementing") else template.format("5.4", topic)
        else:
            title = template
        
        ml_score = random.uniform(0.5, 0.9)
        predicted_categories = random.sample(OHDSI_CATEGORIES, random.randint(1, 3))
        
        item = {
            "title": title,
            "abstract": fake.text(max_nb_chars=300),
            "content": fake.text(max_nb_chars=1000),
            "url": fake.url(),
            "content_type": random.choice(CONTENT_TYPES),
            "submitted_date": fake.date_time_between(
                start_date="-30 days",
                end_date="now"
            ).isoformat(),
            "ml_score": ml_score,
            "predicted_categories": predicted_categories,
            "status": "pending",
            "priority": random.randint(0, 10)
        }
        
        items.append(item)
    
    return items

def load_data_to_elasticsearch():
    """Load sample data into Elasticsearch"""
    es = Elasticsearch(settings.elasticsearch_url)
    
    print("Generating sample content...")
    content_items = generate_sample_content(100)
    review_items = generate_review_items(20)
    
    print(f"Loading {len(content_items)} items into content index...")
    approved_count = 0
    for item in content_items:
        if item["approval_status"] == "approved":
            try:
                es.index(
                    index=settings.content_index,
                    body=item,
                    id=fake.uuid4()
                )
                approved_count += 1
            except Exception as e:
                print(f"Failed to index content: {e}")
    
    print(f"Loaded {approved_count} approved items into content index")
    
    print(f"Loading {len(review_items)} items into review queue...")
    review_count = 0
    for item in review_items:
        try:
            es.index(
                index=settings.review_index,
                body=item,
                id=fake.uuid4()
            )
            review_count += 1
        except Exception as e:
            print(f"Failed to index review item: {e}")
    
    print(f"Loaded {review_count} items into review queue")
    
    # Refresh indices to make data searchable immediately
    es.indices.refresh(index=settings.content_index)
    es.indices.refresh(index=settings.review_index)
    
    return approved_count, review_count

def main():
    """Main function"""
    print("=" * 50)
    print("Loading Sample Data")
    print("=" * 50)
    
    approved, review = load_data_to_elasticsearch()
    
    print("=" * 50)
    print(f"Sample data loaded successfully!")
    print(f"- {approved} approved content items")
    print(f"- {review} review queue items")
    print("=" * 50)

if __name__ == "__main__":
    main()