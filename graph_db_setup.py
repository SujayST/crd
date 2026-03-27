from neo4j import GraphDatabase
import json
import logging
from pathlib import Path
from collections import defaultdict
import numpy as np
import unicodedata
import re
from typing import Dict, List, Optional, Any
import hashlib
import getpass
import datetime

logger = logging.getLogger(__name__)
logger.setLevel(logging.ERROR)


class MultiProjectGraphBuilder:
    """
    Neo4j graph builder with:
    Project → Domain → Segment → Topic → Chunk → Iteration → Summary
    """

    def __init__(
        self,
        neo4j_uri: str = "neo4j://localhost:7687",
        neo4j_user: str = "neo4j",
        neo4j_password: str = "neo4j",
        embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    ):
        try:
            self.driver = GraphDatabase.driver(
                neo4j_uri,
                auth=(neo4j_user, neo4j_password),
                max_connection_lifetime=3600,
                connection_timeout=30
            )
            with self.driver.session() as session:
                session.run("RETURN 1")
        except Exception as e:
            raise ConnectionError(f"Cannot connect to Neo4j: {e}")

        try:
            from sentence_transformers import SentenceTransformer
            self.embedder = SentenceTransformer(embedding_model)
        except Exception as e:
            raise RuntimeError(f"Cannot load embedding model: {e}")

        self.current_user = None

    def close(self):
        if self.driver:
            self.driver.close()

    # ============================
    # PASSWORD HASHING
    # ============================

    def _hash_password(self, password: str) -> str:
        return hashlib.sha256(password.encode()).hexdigest()

    # ============================
    # AUTH — USER + PROJECT
    # ============================

    def create_user_and_project(self, username, password, project_name, pid):
        password_hash = self._hash_password(password)

        try:
            with self.driver.session() as session:
                result = session.run(
                    """
                    OPTIONAL MATCH (existing_user:User {username: $username})
                    WITH existing_user
                    WHERE existing_user IS NULL

                    CREATE (u:User {
                        username: $username,
                        password_hash: $password_hash,
                        created_at: datetime()
                    })

                    MERGE (p:Project {project_id: $pid})
                    ON CREATE SET 
                        p.project_name = $project_name,
                        p.created_at = datetime(),
                        p.updated_at = datetime(),
                        p.current_iteration = 0

                    CREATE (u)-[:OWNS]->(p)

                    RETURN u.username AS username, 
                           p.project_id AS project_id, 
                           p.project_name AS project_name
                    """,
                    username=username,
                    password_hash=password_hash,
                    pid=pid,
                    project_name=project_name
                ).single()

                if not result:
                    return {"success": False, "error": "Username already exists"}

                self.current_user = username
                return {"success": True, "user": username, "project": dict(result)}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def authenticate(self, username, password):
        password_hash = self._hash_password(password)

        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (u:User {username: $username, password_hash: $password_hash})
                RETURN u.username AS username
                """,
                username=username,
                password_hash=password_hash
            ).single()

            if result:
                self.current_user = username
                return True

        return False

    # ============================
    # PROJECT ACCESS CHECK
    # ============================

    def _verify_project_access(self, project_id: str) -> bool:
        if not self.current_user:
            return False

        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (u:User {username: $username})-[:OWNS]->(p:Project {project_id: $project_id})
                RETURN p.project_id
                """,
                username=self.current_user,
                project_id=project_id
            ).single()

            return result is not None

    # ============================
    # UPDATE PROJECT TIMESTAMP
    # ============================

    def _update_project_timestamp(self, project_id: str):
        """
        Updates project updated_at timestamp after ingestion.
        """
        try:
            with self.driver.session() as session:
                session.run(
                    """
                    MATCH (p:Project {project_id: $project_id})
                    SET p.updated_at = datetime()
                    """,
                    project_id=project_id
                )
        except Exception as e:
            logger.error(f"Failed to update project timestamp: {e}")

    # ============================
    # DOMAIN HANDLING
    # ============================

    def add_domain_to_project(self, project_id: str, domain: str):
        with self.driver.session() as session:
            session.run(
                """
                MATCH (p:Project {project_id: $project_id})

                MERGE (d:Domain {
                    name: $domain,
                    project_id: $project_id
                })

                SET d.project_name = p.project_name

                MERGE (p)-[:HAS_DOMAIN]->(d)
                """,
                domain=domain,
                project_id=project_id
            )

    # ============================
    # SEGMENT HANDLING
    # ============================

    def add_segment_to_domain(self, project_id: str, domain: str, segment: str):
        with self.driver.session() as session:
            session.run(
                """
                MATCH (d:Domain {name: $domain, project_id: $project_id})

                MERGE (s:Segment {
                    name: $segment,
                    domain: $domain,
                    project_id: $project_id
                })

                SET s.project_name = d.project_name

                MERGE (d)-[:HAS_SEGMENT]->(s)
                """,
                domain=domain,
                segment=segment,
                project_id=project_id
            )

    # ============================
    # GET USER PROJECT
    # ============================

    def get_user_project(self, username: str):
        """
        Returns the project owned by the logged-in user.
        """
        if self.current_user != username:
            return None

        try:
            with self.driver.session() as session:
                result = session.run(
                    """
                    MATCH (u:User {username: $username})-[:OWNS]->(p:Project)
                    RETURN 
                        p.project_id AS project_id,
                        p.project_name AS project_name,
                        p.created_at AS created_at,
                        p.updated_at AS updated_at
                    LIMIT 1
                    """,
                    username=username
                ).single()

                if not result:
                    return None

                return {
                    "project_id": result["project_id"],
                    "project_name": result["project_name"],
                    "created_at": result["created_at"],
                    "updated_at": result["updated_at"]
                }

        except Exception as e:
            logger.error(f"Failed to get user project: {e}")
            return None


    # ============================
    # TEXT NORMALIZATION
    # ============================

    def _normalize_text(self, text: Optional[str]) -> str:
        if not text or not isinstance(text, str):
            return "general"
        text = text.lower().strip()
        text = unicodedata.normalize('NFD', text)
        text = re.sub(r'\s+', ' ', text)
        return text.replace('\u200b', '').replace('\ufeff', '')

    # ============================
    # CHUNK HASH GENERATOR
    # ============================

    def _generate_chunk_hash(
        self,
        project_id: str,
        domain: str,
        segment: str,
        topic: str,
        chunk_text: str
    ) -> str:
        normalized_text = self._normalize_text(chunk_text)
        raw = f"{project_id}|{domain}|{segment}|{topic}|{normalized_text}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    # ============================
    # DEDUPLICATION ENGINE
    # ============================

    def _deduplicate_chunks(self, topic_chunks: List[Dict]) -> tuple:
        text_to_chunks = defaultdict(list)

        for chunk in topic_chunks:
            normalized_text = self._normalize_text(chunk['chunk_text'])
            text_to_chunks[normalized_text].append(chunk)

        deduplicated = []
        duplicate_count = 0

        for normalized_text, chunk_entries in text_to_chunks.items():
            if len(chunk_entries) > 1:
                duplicate_count += len(chunk_entries) - 1
                best_chunk = max(chunk_entries, key=lambda c: c.get('confidence', 0.0))
                deduplicated.append(best_chunk)
            else:
                deduplicated.append(chunk_entries[0])

        return deduplicated, duplicate_count

    # ============================
    # EMBEDDINGS
    # ============================

    def _compute_embeddings(self, chunks: List[Dict]) -> Dict[int, np.ndarray]:
        texts = [chunk['chunk_text'] for chunk in chunks]

        embeddings = self.embedder.encode(
            texts,
            normalize_embeddings=True,
            show_progress_bar=False,
            convert_to_numpy=True
        )

        return {i: embeddings[i] for i in range(len(chunks))}

    # ============================
    # CREATE TOPICS UNDER SEGMENT
    # ============================

    def _create_segment_topics(self, project_id, segment, domain, topics):
        with self.driver.session() as session:
            for topic in topics:
                session.run(
                    """
                    MATCH (s:Segment {
                        name: $segment,
                        domain: $domain,
                        project_id: $project_id
                    })

                    MERGE (t:Topic {
                        name: $topic,
                        segment: $segment,
                        domain: $domain,
                        project_id: $project_id
                    })

                    SET t.project_name = s.project_name

                    MERGE (s)-[:HAS_TOPIC]->(t)
                    """,
                    segment=segment,
                    domain=domain,
                    topic=topic,
                    project_id=project_id
                )

        return len(topics)

    # ============================
    # CREATE ITERATION-AWARE CHUNKS
    # ============================

    def _create_topic_chunks(self, project_id, domain, segment, chunks,iteration):
        """
        Creates chunks with iteration awareness.
        Only new chunks get new iteration number.
        """

        new_chunk_hashes = []

        with self.driver.session() as session:
            for chunk in chunks:
                normalized_topic = self._normalize_text(chunk["topic"])

                chunk_hash = self._generate_chunk_hash(
                    project_id,
                    domain,
                    segment,
                    normalized_topic,
                    chunk["chunk_text"]
                )

                result = session.run(
                    """
                    MATCH (t:Topic {
                        name: $topic,
                        project_id: $project_id,
                        domain: $domain,
                        segment: $segment
                    })

                    MERGE (c:Chunk {
                        chunk_hash: $chunk_hash,
                        project_id: $project_id,
                        domain: $domain,
                        segment: $segment,
                        topic: $topic
                    })

                    ON CREATE SET
                        c.text = $text,
                        c.confidence = $confidence,
                        c.created_at = datetime(),
                        c.iteration = $iteration,
                        c.project_name = t.project_name,
                        c._just_created = true

                    MERGE (c)-[:BELONGS_TO]->(t)

                    RETURN coalesce(c._just_created, false) AS created
                    """,
                    project_id=project_id,
                    domain=domain,
                    segment=segment,
                    topic=normalized_topic,
                    chunk_hash=chunk_hash,
                    text=chunk["chunk_text"],
                    confidence=chunk.get("confidence", 0.0),
                    iteration=iteration
                )

                record = result.single()
                if record and record["created"]:
                    new_chunk_hashes.append(chunk_hash)

                session.run(
                    """
                    MATCH (c:Chunk {chunk_hash: $chunk_hash})
                    REMOVE c._just_created
                    """,
                    chunk_hash=chunk_hash
                )

        return new_chunk_hashes, iteration

    # ============================
    # INCREMENTAL SIMILARITY ENGINE
    # ============================

    def _create_project_similarities(
        self,
        project_id,
        domain,
        segment,
        new_chunks,
        embedding_map,
        threshold
    ):
        """
        Similarity rules:
        - New ↔ New
        - New ↔ Old
        - Never Old ↔ Old
        """

        new_hashes = {}
        new_topics = {}

        for i, chunk in enumerate(new_chunks):
            topic = self._normalize_text(chunk["topic"])
            new_hashes[i] = self._generate_chunk_hash(
                project_id, domain, segment, topic, chunk["chunk_text"]
            )
            new_topics[i] = topic

        relationships_created = 0

        with self.driver.session() as session:

            # Existing chunks (older iterations)
            existing = session.run(
                """
                MATCH (c:Chunk {
                    project_id: $project_id,
                    domain: $domain,
                    segment: $segment
                })
                WHERE NOT c.chunk_hash IN $new_hashes
                RETURN c.chunk_hash AS chunk_hash,
                       c.text AS text,
                       c.topic AS topic
                """,
                project_id=project_id,
                domain=domain,
                segment=segment,
                new_hashes=list(new_hashes.values())
            ).data()

            existing_embeddings = {
                r["chunk_hash"]: {
                    "topic": self._normalize_text(r["topic"]),
                    "embedding": self.embedder.encode(
                        [r["text"]],
                        normalize_embeddings=True
                    )[0]
                }
                for r in existing
            }

            # NEW ↔ NEW
            for i in range(len(new_chunks)):
                emb_i = embedding_map[i]
                hash_i = new_hashes[i]
                topic_i = new_topics[i]

                for j in range(i + 1, len(new_chunks)):
                    if topic_i == new_topics[j]:
                        continue

                    sim = float(np.dot(emb_i, embedding_map[j]))
                    if sim < threshold:
                        continue

                    session.run(
                        """
                        MATCH (c1:Chunk {chunk_hash: $h1})
                        MATCH (c2:Chunk {chunk_hash: $h2})
                        MERGE (c1)-[:SIMILAR_TO {similarity: $sim}]-(c2)
                        """,
                        h1=hash_i,
                        h2=new_hashes[j],
                        sim=sim
                    )
                    relationships_created += 1

            # NEW ↔ OLD
            for i in range(len(new_chunks)):
                emb_i = embedding_map[i]
                hash_i = new_hashes[i]
                topic_i = new_topics[i]

                for old_hash, old_data in existing_embeddings.items():
                    if topic_i == old_data["topic"]:
                        continue

                    sim = float(np.dot(emb_i, old_data["embedding"]))
                    if sim < threshold:
                        continue

                    session.run(
                        """
                        MATCH (c1:Chunk {chunk_hash: $h1})
                        MATCH (c2:Chunk {chunk_hash: $h2})
                        MERGE (c1)-[:SIMILAR_TO {similarity: $sim}]-(c2)
                        """,
                        h1=hash_i,
                        h2=old_hash,
                        sim=sim
                    )
                    relationships_created += 1

        return relationships_created
    
    def get_next_iteration(self, project_id: str, domain: str, segment: str) -> int:
        """
        Atomically increments and returns iteration number for a segment.
        """
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (s:Segment {
                    project_id: $project_id,
                    domain: $domain,
                    name: $segment
                })
                SET s.iteration = coalesce(s.iteration, 0) + 1
                RETURN s.iteration AS iteration
                """,
                project_id=project_id,
                domain=domain,
                segment=segment
            ).single()

            return result["iteration"]


    # ============================
    # MAIN GRAPH BUILDER (ITERATION-AWARE)
    # ============================

    def build_project_graph(
        self,
        project_id: str,
        json_file_path: str,
        domain: str,
        segment: str,
        selected_topics: List[str],
        similarity_threshold: float = 0.7
    ) -> Dict[str, Any]:

        if not self._verify_project_access(project_id):
            return {'success': False, 'error': 'Access denied'}

        try:
            if not Path(json_file_path).exists():
                raise FileNotFoundError(f"JSON file not found: {json_file_path}")

            # Ensure hierarchy exists
            self.add_domain_to_project(project_id, domain)
            self.add_segment_to_domain(project_id, domain, segment)

            with open(json_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            all_chunks = data
            normalized_topics = [self._normalize_text(t) for t in selected_topics]

            filtered_chunks = [
                c for c in all_chunks
                if self._normalize_text(c['topic']) in normalized_topics
            ]

            if not filtered_chunks:
                return {'success': False, 'error': 'No chunks found'}

            # Deduplicate
            deduped_chunks, dup_count = self._deduplicate_chunks(filtered_chunks)

            # Create topics
            topics_created = self._create_segment_topics(
                project_id, segment, domain, normalized_topics
            )
            iteration = self.get_next_iteration(project_id, domain, segment)
            # Create chunks with iteration
            new_chunk_hashes, iteration = self._create_topic_chunks(
                project_id, domain, segment, deduped_chunks,iteration
            )

            # Extract truly new chunks
            new_chunks = [
                c for c in deduped_chunks
                if self._generate_chunk_hash(
                    project_id,
                    domain,
                    segment,
                    self._normalize_text(c["topic"]),
                    c["chunk_text"]
                ) in new_chunk_hashes
            ]

            # Compute embeddings & similarity
            relationships_created = 0

            if new_chunks:
                embeddings = self._compute_embeddings(new_chunks)

                relationships_created = self._create_project_similarities(
                    project_id,
                    domain,
                    segment,
                    new_chunks,
                    embeddings,
                    similarity_threshold
                )

            # Update timestamp
            self._update_project_timestamp(project_id)

            return {
                'success': True,
                'project_id': project_id,
                'domain': domain,
                'segment': segment,
                'iteration': iteration,
                'topics_created': topics_created,
                'new_chunks_count': len(new_chunks),
                'chunks_deduplicated': dup_count,
                'relationships_created': relationships_created
            }

        except Exception as e:
            logger.error(f"Graph build failed: {e}")
            return {'success': False, 'error': str(e)}

    # ============================
    # ITERATION 2+ SUMMARY INGESTION
    # ============================

    def ingest_iteration_topic_summaries(
        self,
        project_id: str,
        domain: str,
        segment: str,
        iteration: int,          # 👈 iteration PASSED IN
        iteration_json: Dict
    ) -> int:

        topics_data = iteration_json.get("topics", {})
        created_count = 0

        with self.driver.session() as session:
            for topic_name, payload in topics_data.items():

                normalized_topic = self._normalize_text(topic_name)

                summary_text = payload.get("llm_summary", "")
                followup_questions = payload.get("followup_questions", [])

                stats = {
                    "total_questions": payload.get("total_questions", 0),
                    "answered_count": payload.get("answered_count", 0),
                    "unanswered_count": payload.get("unanswered_count", 0),
                }

                session.run(
                    """
                    MERGE (t:Topic {
                        name: $topic,
                        project_id: $project_id,
                        domain: $domain,
                        segment: $segment
                    })

                    MERGE (s:TopicSummary {
                        topic: $topic,
                        project_id: $project_id,
                        domain: $domain,
                        segment: $segment,
                        iteration: $iteration
                    })

                    ON CREATE SET
                        s.summary_text = $summary_text,
                        s.followup_questions = $followup_questions,
                        s.total_questions = $total_questions,
                        s.answered_count = $answered_count,
                        s.unanswered_count = $unanswered_count,
                        s.created_at = datetime()

                    MERGE (s)-[:SUMMARY_OF]->(t)
                    """,
                    topic=normalized_topic,
                    project_id=project_id,
                    domain=domain,
                    segment=segment,
                    iteration=iteration,
                    summary_text=summary_text,
                    followup_questions=followup_questions,
                    total_questions=stats["total_questions"],
                    answered_count=stats["answered_count"],
                    unanswered_count=stats["unanswered_count"]
                )

                created_count += 1

        return created_count

    # ============================
    # PART 4 — ITERATION QUERY ENGINE
    # ============================

    def get_topic_summary_history(self, project_id: str, topic: str) -> List[Dict[str, Any]]:
        """
        Fetch full LLM summary timeline per topic across iterations.
        """
        if not self._verify_project_access(project_id):
            return []

        normalized_topic = self._normalize_text(topic)

        with self.driver.session() as session:
            results = session.run(
                """
                MATCH (s:TopicSummary {
                    project_id: $project_id,
                    topic: $topic
                })
                RETURN 
                    s.iteration AS iteration,
                    s.summary_text AS summary,
                    s.followup_questions AS followup_questions,
                    s.total_questions AS total_questions,
                    s.answered_count AS answered_count,
                    s.unanswered_count AS unanswered_count,
                    s.created_at AS created_at
                ORDER BY s.iteration ASC
                """,
                project_id=project_id,
                topic=normalized_topic
            )

            return [dict(r) for r in results]

    # ============================
    # GET ALL ITERATIONS PER TOPIC
    # ============================

    def get_topic_iterations(self, project_id: str, topic: str) -> List[int]:
        """
        Get list of iteration numbers where topic appears.
        """
        if not self._verify_project_access(project_id):
            return []

        normalized_topic = self._normalize_text(topic)

        with self.driver.session() as session:
            results = session.run(
                """
                MATCH (c:Chunk {
                    project_id: $project_id,
                    topic: $topic
                })
                RETURN DISTINCT c.iteration AS iteration
                ORDER BY iteration ASC
                """,
                project_id=project_id,
                topic=normalized_topic
            )

            return [r["iteration"] for r in results]

    # ============================
    # COMPARE TWO ITERATIONS
    # ============================

    def compare_topic_iterations(
        self,
        project_id: str,
        topic: str,
        iteration_a: int,
        iteration_b: int
    ) -> Dict[str, Any]:
        """
        Compare chunk evolution between two iterations.
        """
        if not self._verify_project_access(project_id):
            return {}

        normalized_topic = self._normalize_text(topic)

        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (c1:Chunk {
                    project_id: $project_id,
                    topic: $topic,
                    iteration: $iter_a
                })
                WITH collect(c1.text) AS iter_a_chunks

                MATCH (c2:Chunk {
                    project_id: $project_id,
                    topic: $topic,
                    iteration: $iter_b
                })

                RETURN 
                    iter_a_chunks,
                    collect(c2.text) AS iter_b_chunks
                """,
                project_id=project_id,
                topic=normalized_topic,
                iter_a=iteration_a,
                iter_b=iteration_b
            ).single()

            return dict(result) if result else {}

    # ============================
    # GET FOLLOW-UP QUESTIONS (LATEST)
    # ============================

    def get_followup_questions(self, project_id: str, topic: str) -> List[str]:
        """
        Fetch latest follow-up questions for a topic.
        """
        if not self._verify_project_access(project_id):
            return []

        normalized_topic = self._normalize_text(topic)

        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (s:TopicSummary {
                    project_id: $project_id,
                    topic: $topic
                })
                RETURN s.followup_questions AS questions
                ORDER BY s.iteration DESC
                LIMIT 1
                """,
                project_id=project_id,
                topic=normalized_topic
            ).single()

            return result["questions"] if result and result["questions"] else []

    # ============================
    # PROJECT ITERATION TIMELINE
    # ============================

    def get_project_iteration_timeline(self, project_id: str) -> Dict[str, Any]:
        """
        Returns overall CRD evolution stats (Django-ready).
        """
        if not self._verify_project_access(project_id):
            return {}

        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (p:Project {project_id: $project_id})

                OPTIONAL MATCH (c:Chunk {project_id: $project_id})
                OPTIONAL MATCH (s:TopicSummary {project_id: $project_id})

                RETURN 
                    p.project_name AS project_name,
                    coalesce(max(c.iteration), 0) AS last_chunk_iteration,
                    coalesce(max(s.iteration), 0) AS last_summary_iteration,
                    count(DISTINCT c) AS total_chunks,
                    count(DISTINCT s) AS total_summaries
                """,
                project_id=project_id
            ).single()

            return dict(result) if result else {}

    # ============================
    # GET TOPIC EVOLUTION SNAPSHOT
    # ============================

    def get_topic_evolution_snapshot(self, project_id: str, topic: str) -> Dict[str, Any]:
        """
        Returns chunk + summary evolution history per topic.
        """
        if not self._verify_project_access(project_id):
            return {}

        normalized_topic = self._normalize_text(topic)

        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (t:Topic {
                    project_id: $project_id,
                    name: $topic
                })

                OPTIONAL MATCH (c:Chunk {
                    project_id: $project_id,
                    topic: $topic
                })

                OPTIONAL MATCH (s:TopicSummary {
                    project_id: $project_id,
                    topic: $topic
                })

                RETURN 
                    t.name AS topic,
                    collect(DISTINCT c.iteration) AS chunk_iterations,
                    collect(DISTINCT s.iteration) AS summary_iterations,
                    count(DISTINCT c) AS total_chunks,
                    count(DISTINCT s) AS total_summaries
                """,
                project_id=project_id,
                topic=normalized_topic
            ).single()

            return dict(result) if result else {}

    # ============================
    # FETCH CHUNKS BY ITERATION
    # ============================

    def get_chunks_by_iteration(
        self,
        project_id: str,
        topic: str,
        iteration: int
    ) -> List[Dict[str, Any]]:
        """
        Fetch chunk text for specific topic iteration.
        """
        if not self._verify_project_access(project_id):
            return []

        normalized_topic = self._normalize_text(topic)

        with self.driver.session() as session:
            results = session.run(
                """
                MATCH (c:Chunk {
                    project_id: $project_id,
                    topic: $topic,
                    iteration: $iteration
                })
                RETURN 
                    c.chunk_hash AS chunk_hash,
                    c.text AS text,
                    c.confidence AS confidence,
                    c.created_at AS created_at
                ORDER BY c.confidence DESC
                """,
                project_id=project_id,
                topic=normalized_topic,
                iteration=iteration
            )

            return [dict(r) for r in results]

    # ============================
    # FETCH ALL TOPIC STATS (UI READY)
    # ============================

    def get_topic_statistics(self, project_id: str) -> List[Dict[str, Any]]:
        """
        Returns per-topic metrics for dashboard UI.
        """
        if not self._verify_project_access(project_id):
            return []

        with self.driver.session() as session:
            results = session.run(
                """
                MATCH (t:Topic {project_id: $project_id})
                OPTIONAL MATCH (t)<-[:BELONGS_TO]-(c:Chunk)
                OPTIONAL MATCH (s:TopicSummary {project_id: $project_id, topic: t.name})

                RETURN 
                    t.name AS topic,
                    count(DISTINCT c) AS total_chunks,
                    max(c.iteration) AS latest_chunk_iteration,
                    max(s.iteration) AS latest_summary_iteration
                ORDER BY total_chunks DESC
                """,
                project_id=project_id
            )

            return [dict(r) for r in results]

    # ============================
    # GET AVAILABLE TOPICS FROM JSON
    # ============================

    def get_available_topics_from_json(self, json_file_path: str) -> List[str]:
        """
        Extract unique topics from chunk JSON file.
        JSON format: List of chunk objects.
        """
        try:
            with open(json_file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            topics = {
            self._normalize_text(chunk.get("topic"))
            for chunk in data
            if isinstance(chunk, dict)
        }


            return sorted(topics)

        except Exception as e:
            logger.error(f"Failed to read topics from JSON: {e}")
            return []


    # ============================
    # QUERY SEGMENT TOPICS
    # ============================

    def query_segment_topics(self, project_id: str) -> List[Dict[str, Any]]:
        if not self._verify_project_access(project_id):
            return []

        try:
            with self.driver.session() as session:
                result = session.run(
                    """
                    MATCH (p:Project {project_id: $project_id})
                          -[:HAS_DOMAIN]->(d:Domain)
                          -[:HAS_SEGMENT]->(s:Segment)
                          -[:HAS_TOPIC]->(t:Topic)

                    OPTIONAL MATCH (t)<-[:BELONGS_TO]-(c:Chunk)

                    RETURN 
                        d.name AS domain,
                        s.name AS segment,
                        t.name AS topic,
                        count(DISTINCT c) AS chunk_count,
                        avg(c.confidence) AS avg_confidence

                    ORDER BY chunk_count DESC
                    """,
                    project_id=project_id
                )

                return [dict(record) for record in result]

        except Exception as e:
            logger.error(f"Query topics failed: {e}")
            return []


    # ============================
    # QUERY TOPIC CHUNKS
    # ============================

    def query_topic_chunks(self, project_id: str, topic_name: str) -> List[Dict[str, Any]]:
        if not self._verify_project_access(project_id):
            return []

        try:
            with self.driver.session() as session:
                result = session.run(
                    """
                    MATCH (t:Topic {
                        name: $topic,
                        project_id: $project_id
                    })<-[:BELONGS_TO]-(c:Chunk)

                    RETURN 
                        c.chunk_hash AS chunk_hash,
                        c.text AS text,
                        c.confidence AS confidence,
                        c.iteration AS iteration

                    ORDER BY c.confidence DESC
                    """,
                    project_id=project_id,
                    topic=topic_name
                )

                return [dict(record) for record in result]

        except Exception as e:
            logger.error(f"Query chunks failed: {e}")
            return []


    # ============================
    # DISPLAY TOPIC CHUNKS
    # ============================

    def display_topic_chunks(self, project_id: str, topic_name: str, limit: Optional[int] = None):
        chunks = self.query_topic_chunks(project_id, topic_name)

        if not chunks:
            print(f"No chunks found for topic '{topic_name}'")
            return

        print(f"\n{'='*80}")
        print(f"Topic: {topic_name}")
        print(f"Total Chunks: {len(chunks)}")
        print(f"{'='*80}\n")

        display_chunks = chunks[:limit] if limit else chunks

        for i, chunk in enumerate(display_chunks, 1):
            print(f"Chunk #{i}")
            print(f"Iteration: {chunk.get('iteration')}")
            print(f"Confidence: {chunk.get('confidence')}")
            print(f"Text: {chunk['text'][:300]}{'...' if len(chunk['text']) > 300 else ''}")
            print(f"{'-'*80}\n")


    # ============================
    # QUERY SIMILAR CHUNKS
    # ============================

    def query_similar_chunks(
        self,
        project_id: str,
        chunk_hash: str,
        min_similarity: float = 0.0,
        limit: Optional[int] = 10
    ) -> List[Dict[str, Any]]:

        if not self._verify_project_access(project_id):
            return []

        try:
            with self.driver.session() as session:
                query = """
                MATCH (c1:Chunk {
                    chunk_hash: $chunk_hash,
                    project_id: $project_id
                })-[s:SIMILAR_TO]-(c2:Chunk)

                WHERE s.similarity >= $min_similarity

                RETURN 
                    c2.chunk_hash AS chunk_hash,
                    c2.topic AS topic,
                    c2.text AS text,
                    s.similarity AS similarity

                ORDER BY s.similarity DESC
                """

                if limit:
                    query += f" LIMIT {limit}"

                result = session.run(
                    query,
                    chunk_hash=chunk_hash,
                    project_id=project_id,
                    min_similarity=min_similarity
                )

                return [dict(record) for record in result]

        except Exception as e:
            logger.error(f"Query similar chunks failed: {e}")
            return []


    # ============================
    # GET PROJECT HIERARCHY
    # ============================

    def get_project_hierarchy(self, project_id: str) -> Dict[str, Any]:
        if not self._verify_project_access(project_id):
            return {}

        try:
            with self.driver.session() as session:
                result = session.run(
                    """
                    MATCH (p:Project {project_id: $project_id})
                    OPTIONAL MATCH (p)-[:HAS_DOMAIN]->(d:Domain)
                    OPTIONAL MATCH (d)-[:HAS_SEGMENT]->(s:Segment)
                    OPTIONAL MATCH (s)-[:HAS_TOPIC]->(t:Topic)

                    WITH p, d, s, collect(DISTINCT t.name) AS topics

                    WITH p, d, collect({
                        segment: s.name,
                        topics: topics
                    }) AS segments

                    RETURN 
                        p.project_id AS project_id,
                        p.project_name AS project_name,
                        collect({
                            domain: d.name,
                            segments: segments
                        }) AS hierarchy
                    """,
                    project_id=project_id
                ).single()

                if not result:
                    return {}

                return {
                    "project_id": result["project_id"],
                    "project_name": result["project_name"],
                    "hierarchy": result["hierarchy"]
                }

        except Exception as e:
            logger.error(f"Failed to get hierarchy: {e}")
            return {}

