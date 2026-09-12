"""Seed the Master Skill Registry - the Single Source of Truth for Skill IDs.

Idempotent: re-running updates names/categories and adds missing aliases.

    python seed_skills.py
"""
from sqlalchemy import select

from app.database import Base, SessionLocal, engine
from app.models import Skill, SkillAlias

# (skill_id, canonical_name, category, parent_skill_id, aliases)
SKILLS: list[tuple[str, str, str, str | None, list[str]]] = [
    # --- Programming languages: SKL-1xx ---
    ("SKL-101", "Python", "Programming Language", None, ["py", "python3", "python 3", "cpython"]),
    ("SKL-102", "Java", "Programming Language", None, ["core java", "java se", "jdk"]),
    ("SKL-103", "JavaScript", "Programming Language", None, ["js", "ecmascript", "es6", "vanilla js"]),
    ("SKL-104", "TypeScript", "Programming Language", None, ["ts"]),
    ("SKL-105", "C++", "Programming Language", None, ["cpp", "c plus plus", "cplusplus"]),
    ("SKL-106", "C", "Programming Language", None, ["c language", "ansi c"]),
    ("SKL-107", "C#", "Programming Language", None, ["c sharp", "csharp", "dotnet c#"]),
    ("SKL-108", "Go", "Programming Language", None, ["golang"]),
    ("SKL-109", "Rust", "Programming Language", None, ["rust lang"]),
    ("SKL-110", "Kotlin", "Programming Language", None, []),
    ("SKL-111", "Swift", "Programming Language", None, ["swift lang"]),
    ("SKL-112", "PHP", "Programming Language", None, []),
    ("SKL-113", "R", "Programming Language", None, ["r language", "r lang"]),
    ("SKL-114", "Scala", "Programming Language", None, []),

    # --- Web frontend: SKL-2xx ---
    ("SKL-201", "HTML", "Web Frontend", None, ["html5", "hypertext markup language"]),
    ("SKL-202", "CSS", "Web Frontend", None, ["css3", "cascading style sheets"]),
    ("SKL-203", "React", "Web Frontend", "SKL-103", ["reactjs", "react.js", "react js"]),
    ("SKL-204", "Next.js", "Web Frontend", "SKL-203", ["nextjs", "next js"]),
    ("SKL-205", "Angular", "Web Frontend", "SKL-104", ["angularjs", "angular 2+"]),
    ("SKL-206", "Vue.js", "Web Frontend", "SKL-103", ["vue", "vuejs", "vue js"]),
    ("SKL-207", "Tailwind CSS", "Web Frontend", "SKL-202", ["tailwind", "tailwindcss"]),
    ("SKL-208", "Bootstrap", "Web Frontend", "SKL-202", ["bootstrap5"]),
    ("SKL-209", "Redux", "Web Frontend", "SKL-203", ["redux toolkit", "rtk"]),

    # --- Backend & APIs: SKL-3xx ---
    ("SKL-301", "Node.js", "Backend", "SKL-103", ["nodejs", "node", "node js"]),
    ("SKL-302", "Express.js", "Backend", "SKL-301", ["express", "expressjs"]),
    ("SKL-303", "Django", "Backend", "SKL-101", ["django rest framework", "drf"]),
    ("SKL-304", "Flask", "Backend", "SKL-101", []),
    ("SKL-305", "FastAPI", "Backend", "SKL-101", ["fast api"]),
    ("SKL-306", "Spring Boot", "Backend", "SKL-102", ["springboot", "spring"]),
    ("SKL-307", "REST API", "Backend", None, ["rest", "restful api", "restful services"]),
    ("SKL-308", "GraphQL", "Backend", None, ["graph ql"]),
    ("SKL-309", "Microservices", "Backend", None, ["micro services", "microservice architecture"]),
    ("SKL-310", ".NET", "Backend", "SKL-107", ["dotnet", "asp.net", "asp net core"]),

    # --- Databases: SKL-4xx ---
    ("SKL-401", "SQL", "Database", None, ["structured query language", "ansi sql"]),
    ("SKL-402", "PostgreSQL", "Database", "SKL-401", ["postgres", "psql", "postgre sql"]),
    ("SKL-403", "MySQL", "Database", "SKL-401", ["my sql", "mariadb"]),
    ("SKL-404", "MongoDB", "Database", None, ["mongo", "mongo db"]),
    ("SKL-405", "Redis", "Database", None, []),
    ("SKL-406", "Database Design", "Database", None, ["schema design", "er modelling", "data modeling"]),
    ("SKL-407", "Elasticsearch", "Database", None, ["elastic search", "opensearch"]),

    # --- Data science, AI & ML: SKL-5xx ---
    ("SKL-501", "Machine Learning", "AI/ML", None, ["ml", "machine-learning", "statistical learning"]),
    ("SKL-502", "Deep Learning", "AI/ML", "SKL-501", ["dl", "neural networks", "ann"]),
    ("SKL-503", "Natural Language Processing", "AI/ML", "SKL-501", ["nlp", "text mining"]),
    ("SKL-504", "Computer Vision", "AI/ML", "SKL-502", ["cv", "image processing", "opencv"]),
    ("SKL-505", "TensorFlow", "AI/ML", "SKL-502", ["tensor flow", "keras"]),
    ("SKL-506", "PyTorch", "AI/ML", "SKL-502", ["torch", "py torch"]),
    ("SKL-507", "scikit-learn", "AI/ML", "SKL-501", ["sklearn", "scikit learn"]),
    ("SKL-508", "Pandas", "Data Science", "SKL-101", ["pandas library"]),
    ("SKL-509", "NumPy", "Data Science", "SKL-101", ["numpy library", "np"]),
    ("SKL-510", "Data Analysis", "Data Science", None, ["data analytics", "exploratory data analysis", "eda"]),
    ("SKL-511", "Data Visualization", "Data Science", None, ["dataviz", "matplotlib", "power bi", "tableau"]),
    ("SKL-512", "Large Language Models", "AI/ML", "SKL-503", ["llm", "llms", "generative ai", "gen ai"]),

    # --- Cloud & DevOps: SKL-6xx ---
    ("SKL-601", "Docker", "DevOps", None, ["containerization", "containers"]),
    ("SKL-602", "Kubernetes", "DevOps", "SKL-601", ["k8s", "kube"]),
    ("SKL-603", "AWS", "Cloud", None, ["amazon web services", "ec2", "s3"]),
    ("SKL-604", "Microsoft Azure", "Cloud", None, ["azure"]),
    ("SKL-605", "Google Cloud Platform", "Cloud", None, ["gcp", "google cloud"]),
    ("SKL-606", "CI/CD", "DevOps", None, ["continuous integration", "continuous delivery", "github actions", "jenkins"]),
    ("SKL-607", "Linux", "DevOps", None, ["unix", "shell scripting", "bash"]),
    ("SKL-608", "Terraform", "DevOps", None, ["infrastructure as code", "iac"]),

    # --- Tools & engineering practice: SKL-7xx ---
    ("SKL-701", "Git", "Tools", None, ["github", "gitlab", "version control"]),
    ("SKL-702", "Data Structures & Algorithms", "Computer Science", None, ["dsa", "algorithms", "data structures"]),
    ("SKL-703", "Operating Systems", "Computer Science", None, ["os", "operating system"]),
    ("SKL-704", "Computer Networks", "Computer Science", None, ["networking", "tcp/ip"]),
    ("SKL-705", "Object Oriented Programming", "Computer Science", None, ["oop", "oops"]),
    ("SKL-706", "Software Testing", "Engineering Practice", None, ["unit testing", "qa", "pytest", "junit"]),
    ("SKL-707", "System Design", "Engineering Practice", None, ["hld", "lld", "architecture design"]),
    ("SKL-708", "Agile & Scrum", "Engineering Practice", None, ["agile", "scrum", "kanban"]),
    ("SKL-709", "Cyber Security", "Security", None, ["security", "infosec", "application security"]),

    # --- Mobile: SKL-8xx ---
    ("SKL-801", "Android Development", "Mobile", "SKL-110", ["android", "android studio"]),
    ("SKL-802", "iOS Development", "Mobile", "SKL-111", ["ios", "swiftui"]),
    ("SKL-803", "React Native", "Mobile", "SKL-203", ["react-native", "rn"]),
    ("SKL-804", "Flutter", "Mobile", None, ["dart", "flutter sdk"]),

    # --- Professional skills: SKL-9xx ---
    ("SKL-901", "Communication", "Soft Skill", None, ["verbal communication", "written communication"]),
    ("SKL-902", "Teamwork", "Soft Skill", None, ["collaboration", "team work"]),
    ("SKL-903", "Problem Solving", "Soft Skill", None, ["analytical thinking", "critical thinking"]),
    ("SKL-904", "Project Management", "Soft Skill", None, ["jira", "sprint planning"]),
    ("SKL-905", "Leadership", "Soft Skill", None, ["team leadership", "mentoring"]),
]


def seed() -> tuple[int, int]:
    Base.metadata.create_all(bind=engine)
    created = updated = 0
    with SessionLocal() as db:
        # Parents are inserted in the same pass; defer FK resolution by ordering
        # on the fact that parents always have a lower id in this list.
        for skill_id, name, category, parent, aliases in SKILLS:
            skill = db.get(Skill, skill_id)
            if skill is None:
                skill = Skill(id=skill_id)
                db.add(skill)
                created += 1
            else:
                updated += 1
            skill.canonical_name = name
            skill.category = category
            skill.parent_skill_id = parent
            db.flush()

            known = {a.alias for a in skill.aliases}
            for alias in aliases:
                alias = alias.strip().lower()
                if alias in known:
                    continue
                if db.scalar(select(SkillAlias).where(SkillAlias.alias == alias)):
                    continue  # alias already claimed by another skill
                db.add(SkillAlias(skill_id=skill_id, alias=alias))
        db.commit()
    return created, updated


if __name__ == "__main__":
    created, updated = seed()
    print(f"Master Skill Registry seeded: {created} created, {updated} updated, {len(SKILLS)} total.")
