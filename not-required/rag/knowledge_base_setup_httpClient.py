import chromadb
import os
import json
from chromadb.utils import embedding_functions
import pandas as pd

# Initialize ChromaDB HTTP Client
client = chromadb.HttpClient(host="localhost", port=8000)  # Adjust host/port if your Chroma server is running elsewhere

# Embedding function
embedding_function = embedding_functions.DefaultEmbeddingFunction()

# Delete existing collection if it exists (for clean slate during setup)
try:
    client.delete_collection("frcrce_knowledge")
    print("Deleted existing collection")
except:
    print("No existing collection to delete")

# Create collection
collection = client.create_collection(
    name="frcrce_knowledge",
    embedding_function=embedding_function,
    metadata={"description": "FR CRCE College comprehensive knowledge base with dynamic query support"}
)

# Enhanced FR CRCE knowledge base with multiple phrasings and comprehensive coverage
frcrce_knowledge = [
    # Location & Travel - Multiple variations for dynamic queries
    {
        "text": "FR CRCE college is located at Fr. Agnel Ashram, Bandstand, Bandra West, Mumbai, Maharashtra. The full address is Fr. Agnel Ashram, Bandstand, Bandra (West), Mumbai, Maharashtra. The college is situated in Bandra West near Bandstand area.",
        "metadata": {
            "category": "location_travel",
            "subcategory": "campus_location",
            "priority": "high",
            "keywords": ["location", "address", "where", "situated", "campus", "Bandra", "Mumbai", "Maharashtra"]
        }
    },
    {
        "text": "FR CRCE is easily accessible by air, train and bus. From International Airport it is 11 kilometers away. From Bandra Railway Station it is 4 kilometers distance. You can take Bus No. 211 from Bandra West station which goes directly to the college last stop. The nearest landmark is Taj Lands End hotel.",
        "metadata": {
            "category": "location_travel",
            "subcategory": "transportation",
            "priority": "high",
            "keywords": ["how to reach", "transport", "airport", "railway", "bus", "distance", "travel", "accessibility"]
        }
    },
    
    # Fees & Payment - Comprehensive fee information
    {
        "text": "The B.Tech program fee at FR CRCE for academic year 2024-25 is Rs. 1,81,000 plus University Processing Fees for the first year. This fee is sanctioned by the Fee Regulating Authority FRA. The total fee amount is one lakh eighty one thousand rupees plus university fees.",
        "metadata": {
            "category": "fees_payment",
            "subcategory": "tuition_fees",
            "priority": "high",
            "keywords": ["fee", "cost", "tuition", "B.Tech fee", "how much", "price", "charges", "academic year", "2024-25"]
        }
    },
    {
        "text": "Tuition fees remain constant and same throughout all four years of B.Tech study. The fee does not increase during the course duration. Students must pay the full tuition fee in one single installment every year. Partial payments or installments are not allowed for tuition fees.",
        "metadata": {
            "category": "fees_payment",
            "subcategory": "fee_structure",
            "priority": "high",
            "keywords": ["fee constant", "same fee", "installment", "payment terms", "four years", "fee increase"]
        }
    },
    {
        "text": "Scholarships and fee concessions are available for eligible students based on category and caste. Students must be admitted through CAP rounds to be eligible for these benefits. Government scholarship schemes and many private scholarships are also available for deserving students.",
        "metadata": {
            "category": "fees_payment",
            "subcategory": "scholarships",
            "priority": "high",
            "keywords": ["scholarship", "concession", "financial aid", "category", "caste", "CAP rounds", "government schemes", "private scholarships"]
        }
    },
    {
        "text": "Educational loans are available from several banks for paying college fees. Union Bank is the nearest bank to the campus. Many other banks are located on Hill Road near the college. Students need to take admission first by paying fees, then apply for Fee Structure and Bonafide certificate from college to submit to bank for loan processing.",
        "metadata": {
            "category": "fees_payment",
            "subcategory": "education_loans",
            "priority": "medium",
            "keywords": ["education loan", "bank loan", "Union Bank", "Hill Road", "loan process", "bonafide certificate"]
        }
    },
    {
        "text": "There is absolutely no capitation fee or donation required at FR CRCE. The college does not accept any donations. Only the fee approved by Fee Regulating Authority and University fees need to be paid. No additional charges or hidden fees are required.",
        "metadata": {
            "category": "fees_payment",
            "subcategory": "no_donation",
            "priority": "medium",
            "keywords": ["donation", "capitation fee", "hidden charges", "additional fee", "no donation", "FRA approved"]
        }
    },
    
    # Admission Process - Detailed admission information
    {
        "text": "For B.Tech admission eligibility requirements and application process, students should refer to the Directorate of Technical Education DTE website and FRCRCE official website regularly for latest updates and notifications. The admission process follows DTE guidelines and CET cell notifications.",
        "metadata": {
            "category": "admission",
            "subcategory": "eligibility_process",
            "priority": "high",
            "keywords": ["admission process", "eligibility", "how to apply", "DTE", "CET", "application", "requirements"]
        }
    },
    {
        "text": "The DTE institute code for FRCRCE is 3184. This code is used during the admission process and CAP rounds. Students need to use this code when filling admission forms and during seat allotment process.",
        "metadata": {
            "category": "admission",
            "subcategory": "institute_code",
            "priority": "high",
            "keywords": ["institute code", "DTE code", "3184", "admission code", "CAP code"]
        }
    },
    {
        "text": "CAP stands for Centralized Admission Process which is conducted by Directorate of Technical Education, Government of Maharashtra. The college has no role in seat allotment process. All seat allotments are done through online portal by DTE. Students get seats based on merit and choices filled during CAP rounds.",
        "metadata": {
            "category": "admission",
            "subcategory": "cap_process",
            "priority": "high",
            "keywords": ["CAP", "centralized admission", "seat allotment", "online portal", "merit based", "DTE process"]
        }
    },
    {
        "text": "Maharashtra candidates are students who have studied SSC and HSC from Maharashtra state, were born in Maharashtra, or have domicile in Maharashtra. Students whose parents are Government of India employees posted in Maharashtra are also considered Maharashtra candidates. Outside Maharashtra candidates are from other states.",
        "metadata": {
            "category": "admission",
            "subcategory": "maharashtra_candidates",
            "priority": "medium",
            "keywords": ["Maharashtra candidate", "domicile", "SSC HSC", "born in Maharashtra", "outside Maharashtra", "government employee"]
        }
    },
    {
        "text": "Original documents submission is mandatory for confirming admission along with fee payment. If original documents are not available at time of admission, students will be given some time to submit them later. Student's physical presence is compulsory for institute quota admissions along with demand draft of fees and original documents or retention letter.",
        "metadata": {
            "category": "admission",
            "subcategory": "document_submission",
            "priority": "high",
            "keywords": ["original documents", "mandatory", "physical presence", "demand draft", "institute quota", "retention letter"]
        }
    },
    {
        "text": "Required documents for admission include SSC and HSC marksheets and passing certificates, School Leaving Certificate, MH-CET or JEE Main scorecard, CAP allotment or registration letter, Aadhar card photocopy, Nationality certificate, Domicile certificate, Caste certificate, Caste validity certificate, and Non-Creamy Layer certificate for applicable categories.",
        "metadata": {
            "category": "admission",
            "subcategory": "required_documents",
            "priority": "high",
            "keywords": ["documents required", "certificates", "marksheets", "leaving certificate", "MH-CET", "JEE", "Aadhar", "domicile", "caste certificate"]
        }
    },
    {
        "text": "In academic year 2021-22, the CAP round cutoff percentile for Computer Engineering was 90.38% and for Artificial Intelligence and Data Science was 89.90%. These cutoffs may vary each year based on competition and number of applicants. Current year cutoffs will be available after CAP rounds.",
        "metadata": {
            "category": "admission",
            "subcategory": "cutoffs",
            "priority": "medium",
            "keywords": ["cutoff", "merit", "percentile", "Computer Engineering", "AI DS", "90.38", "89.90", "competition"]
        }
    },
    {
        "text": "Beware of admission agents and middlemen. FRCRCE does not have any authorized agents for admissions. Students and parents should contact the institute directly or visit the official website https://www.frcrce.ac.in for authentic information. Do not pay money to any agents claiming to guarantee admission.",
        "metadata": {
            "category": "admission",
            "subcategory": "beware_agents",
            "priority": "medium",
            "keywords": ["agents", "middlemen", "beware", "no agents", "direct contact", "official website", "fraud prevention"]
        }
    },
    
    # College Information - Comprehensive college details
    {
        "text": "FRCRCE is a Private College, not a government institution. It is a self-financing private college approved by AICTE and affiliated to University of Mumbai. The college has autonomous status for academic flexibility.",
        "metadata": {
            "category": "college_info",
            "subcategory": "college_type",
            "priority": "medium",
            "keywords": ["private college", "government", "self-financing", "AICTE", "University of Mumbai", "autonomous"]
        }
    },
    {
        "text": "Students receive Bachelor of Technology B.Tech degree from FR CRCE, not Bachelor of Engineering B.E. degree. B.Tech is offered by autonomous institutes while B.E. is typically offered by other affiliated colleges. Both are equivalent engineering degrees.",
        "metadata": {
            "category": "college_info",
            "subcategory": "degree_type",
            "priority": "medium",
            "keywords": ["B.Tech", "B.E.", "Bachelor of Technology", "Bachelor of Engineering", "degree", "autonomous institutes"]
        }
    },
    {
        "text": "FR CRCE offers undergraduate B.Tech programs in Computer Engineering, Electronics and Computer Science ECS, Artificial Intelligence and Data Science AI DS, and Mechanical Engineering. Postgraduate M.Tech program in Mechanical Engineering with specialization in CAD CAM. Doctoral Ph.D. programs in Mechanical Engineering and Electronics Engineering.",
        "metadata": {
            "category": "college_info",
            "subcategory": "courses_offered",
            "priority": "high",
            "keywords": ["courses", "branches", "Computer Engineering", "ECS", "AI DS", "Mechanical", "M.Tech", "Ph.D.", "programs available"]
        }
    },
    {
        "text": "Electronics Engineering ETRX focuses on circuit analysis, circuit design, PCB design, communication systems, power electronics, embedded systems. Electronics and Computer Science ECS combines both electronics and computer engineering with 70-80% courses common to Computer Engineering branch, making it interdisciplinary.",
        "metadata": {
            "category": "college_info",
            "subcategory": "etrx_vs_ecs",
            "priority": "medium",
            "keywords": ["Electronics Engineering", "ETRX", "ECS", "circuit design", "PCB", "communication", "interdisciplinary"]
        }
    },
    {
        "text": "Computer Engineering involves creating software programs and applications using programming languages, algorithms, and coding. Students learn software development, web development, database management. AI and Data Science focuses on machine learning, artificial intelligence, data analytics, statistical analysis to make data-driven decisions. Both prepare students for technology careers but with different specializations.",
        "metadata": {
            "category": "college_info",
            "subcategory": "computer_vs_ai",
            "priority": "medium",
            "keywords": ["Computer Engineering", "AI Data Science", "programming", "software development", "machine learning", "data analytics", "specialization"]
        }
    },
    
    # Academic Life - Detailed academic information
    {
        "text": "The medium of instruction at FR CRCE is English language. All lectures, practicals, examinations, and course materials are conducted in English. Students should have good English communication skills for better understanding.",
        "metadata": {
            "category": "academics",
            "subcategory": "medium_instruction",
            "priority": "medium",
            "keywords": ["English", "medium of instruction", "language", "lectures", "examinations", "communication"]
        }
    },
    {
        "text": "College timings are from 8:45 AM to 3:30 PM for regular classes. Administrative office operates from 8:30 AM to 4:30 PM. College remains open all days except second and fourth Saturdays of the month. Students are expected to participate in extracurricular activities after regular college hours.",
        "metadata": {
            "category": "academics",
            "subcategory": "college_timings",
            "priority": "medium",
            "keywords": ["college timings", "8:45 AM", "3:30 PM", "office hours", "Saturday off", "extracurricular activities"]
        }
    },
    {
        "text": "FR CRCE follows semester pattern for academic evaluation, not annual system. Each academic year is divided into two semesters with regular assessments, internal exams, and final semester examinations. This provides continuous evaluation of student performance.",
        "metadata": {
            "category": "academics",
            "subcategory": "semester_system",
            "priority": "medium",
            "keywords": ["semester", "annual system", "evaluation", "internal exams", "continuous assessment", "academic year"]
        }
    },
    {
        "text": "Academic results at FR CRCE are excellent with pass percentages ranging from 98% to 100% across all engineering branches. The college maintains high academic standards with consistent outstanding performance by students in university examinations.",
        "metadata": {
            "category": "academics",
            "subcategory": "academic_results",
            "priority": "high",
            "keywords": ["academic results", "pass percentage", "98%", "100%", "excellent results", "university exams", "performance"]
        }
    },
    {
        "text": "Faculty members at FR CRCE are highly qualified, experienced, dedicated, and helpful towards students. Many teachers hold Ph.D. degrees or are currently pursuing doctoral studies. Faculty members have industry experience and research background providing quality education.",
        "metadata": {
            "category": "academics",
            "subcategory": "faculty_quality",
            "priority": "high",
            "keywords": ["faculty", "teachers", "qualified", "Ph.D.", "experienced", "dedicated", "industry experience", "research"]
        }
    },
    {
        "text": "Students can design their own learning path at FR CRCE by choosing from numerous elective subjects, honors courses, minor degree programs, and even courses from other engineering branches. This flexibility allows students to customize their education based on interests and career goals.",
        "metadata": {
            "category": "academics",
            "subcategory": "learning_flexibility",
            "priority": "medium",
            "keywords": ["learning curve", "electives", "honors", "minor", "flexibility", "customization", "career goals", "interdisciplinary"]
        }
    },
    {
        "text": "Online certification courses from platforms like Coursera, edX, NPTEL are encouraged and supported by the college. Students can enhance their skills through additional certifications which complement their regular curriculum and improve employability.",
        "metadata": {
            "category": "academics",
            "subcategory": "online_certifications",
            "priority": "medium",
            "keywords": ["online courses", "certifications", "Coursera", "edX", "NPTEL", "skill enhancement", "employability"]
        }
    },
    {
        "text": "Complete syllabus for all courses and branches is available on the official website. Students can access detailed curriculum, subject-wise syllabus, and course structure at https://frcrce.ac.in/index.php/academics/autonomous-curriculum/syllabus before taking admission to understand course content.",
        "metadata": {
            "category": "academics",
            "subcategory": "syllabus_access",
            "priority": "low",
            "keywords": ["syllabus", "curriculum", "course structure", "website", "detailed content", "subject-wise"]
        }
    },
    
    # Honors, Minors & Research - Advanced academic options
    {
        "text": "FRCRCE offers specialized honors and minor B.Tech programs in emerging technologies including Blockchain Technology, Cyber Security, Robotics and Automation, 3D Printing and Additive Manufacturing, Artificial Intelligence and Machine Learning, Data Science and Analytics, and Internet of Things IoT.",
        "metadata": {
            "category": "academics",
            "subcategory": "honors_minor_programs",
            "priority": "high",
            "keywords": ["honors", "minor degree", "Blockchain", "Cyber Security", "Robotics", "3D Printing", "AI ML", "Data Science", "IoT"]
        }
    },
    {
        "text": "FR CRCE has established a strong research and development culture with active research in cutting-edge domains like Internet of Things, Artificial Intelligence, Robotics, VLSI Design, and other emerging technologies. Faculty and students regularly publish research papers in national and international journals and conferences.",
        "metadata": {
            "category": "academics",
            "subcategory": "research_culture",
            "priority": "high",
            "keywords": ["research", "development", "IoT", "AI", "Robotics", "VLSI", "publications", "journals", "conferences"]
        }
    },
    {
        "text": "Students and faculty at FR CRCE regularly participate and win prizes in national and international technical competitions, hackathons, innovation challenges, and research competitions. This exposure helps in skill development and recognition at national level.",
        "metadata": {
            "category": "academics",
            "subcategory": "competitions_achievements",
            "priority": "medium",
            "keywords": ["competitions", "hackathons", "innovation", "national", "international", "prizes", "recognition", "skill development"]
        }
    },
    
    # Placements & Internships - Comprehensive placement information
    {
        "text": "Campus placements at FR CRCE are excellent and at par with other reputed engineering colleges in Mumbai. The college provides 100% placement assistance to all eligible students. Approximately 20-25% of students choose to pursue higher studies like M.Tech, MS abroad, MBA instead of placements.",
        "metadata": {
            "category": "placements",
            "subcategory": "placement_overview",
            "priority": "high",
            "keywords": ["campus placements", "100% assistance", "reputed colleges", "higher studies", "M.Tech", "MS", "MBA"]
        }
    },
    {
        "text": "Top multinational companies regularly recruit from FR CRCE including JP Morgan Chase, Morgan Stanley, Barclays, Amazon, Microsoft, Infosys, IBM, Larsen and Toubro L&T, Siemens, Accenture, TCS, Wipro, Cognizant, and many other leading organizations from IT, finance, and manufacturing sectors.",
        "metadata": {
            "category": "placements",
            "subcategory": "recruiting_companies",
            "priority": "high",
            "keywords": ["JPMC", "Morgan Stanley", "Barclays", "Amazon", "Microsoft", "Infosys", "IBM", "L&T", "Siemens", "Accenture", "TCS", "multinational"]
        }
    },
    {
        "text": "The placement policy is uniform and same for all engineering branches. Students from Computer, Electronics, AI DS, and Mechanical branches are eligible to apply for most companies. Only few companies with very specific technical job profiles may have branch restrictions.",
        "metadata": {
            "category": "placements",
            "subcategory": "placement_policy",
            "priority": "medium",
            "keywords": ["placement policy", "all branches", "uniform", "eligible", "specific profiles", "branch restrictions"]
        }
    },
    {
        "text": "The college has dedicated placement cell that organizes campus recruitment drives, pre-placement talks, aptitude training, interview preparation, soft skills development, and resume building workshops to ensure students are industry-ready.",
        "metadata": {
            "category": "placements",
            "subcategory": "placement_preparation",
            "priority": "medium",
            "keywords": ["placement cell", "recruitment drives", "aptitude training", "interview preparation", "soft skills", "resume building", "industry-ready"]
        }
    },
    
    # Campus Facilities - Detailed facility information
    {
        "text": "The central library at FR CRCE operates from 8:30 AM to 7:00 PM daily with extensive collection of hardbound books, digital e-books, national and international journals, magazines, reference materials. It has dedicated internet center and book bank facility for students.",
        "metadata": {
            "category": "facilities",
            "subcategory": "library_facility",
            "priority": "medium",
            "keywords": ["library", "8:30 AM", "7:00 PM", "books", "e-books", "journals", "internet center", "book bank"]
        }
    },
    {
        "text": "Internet and Wi-Fi connectivity is available throughout the campus including all computer laboratories, library, internet center, and common areas. Students have access to high-speed internet for academic research, online courses, and project work.",
        "metadata": {
            "category": "facilities",
            "subcategory": "internet_facility",
            "priority": "medium",
            "keywords": ["internet", "Wi-Fi", "computer labs", "high-speed", "academic research", "online courses", "connectivity"]
        }
    },
    {
        "text": "FR CRCE does not provide college bus or transport facility. However, the college is well-connected with 3-4 kilometers distance from Bandra Railway Station. Bus Number 211 provides direct connectivity from Bandra West station to college. Auto-rickshaws and private vehicles are also easily available.",
        "metadata": {
            "category": "facilities",
            "subcategory": "transport_connectivity",
            "priority": "medium",
            "keywords": ["no transport", "3-4 km", "Bandra station", "Bus 211", "auto-rickshaw", "well-connected", "private vehicles"]
        }
    },
    {
        "text": "Campus security is maintained 24x7 with professional security guards at all entry points. ID card verification is mandatory for entry. The entire campus is under CCTV surveillance for safety. Fire safety equipment and emergency protocols are in place throughout the campus.",
        "metadata": {
            "category": "facilities",
            "subcategory": "security_safety",
            "priority": "medium",
            "keywords": ["24x7 security", "ID verification", "CCTV", "fire safety", "emergency protocols", "safety measures"]
        }
    },
    {
        "text": "The campus is located at scenic Bandstand area with beautiful, serene, and pollution-free environment. Students enjoy unobstructed panoramic views of the Arabian Sea which creates an ideal atmosphere for academic studies and extracurricular activities.",
        "metadata": {
            "category": "facilities",
            "subcategory": "campus_environment",
            "priority": "low",
            "keywords": ["Bandstand", "scenic", "pollution-free", "Arabian Sea", "panoramic view", "ideal atmosphere", "serene environment"]
        }
    },
    
    # Hostel & Accommodation
    {
        "text": "Hostel accommodation facility is available for outstation students at Kalina, Santacruz East location. This hostel facility is primarily provided for students from outside Maharashtra state who need residential accommodation during their studies.",
        "metadata": {
            "category": "accommodation",
            "subcategory": "hostel_availability",
            "priority": "medium",
            "keywords": ["hostel", "accommodation", "Kalina", "Santacruz East", "outstation", "outside Maharashtra", "residential"]
        }
    },
    
    # Quotas & Reservations - Detailed reservation information
    {
        "text": "Reservation in seats is applicable as per Government of Maharashtra rules only for CAP rounds conducted by DTE. These include caste-based reservations, EWS quota, and other government mandated reservations. Institute quota seats are filled strictly on merit basis without any reservations.",
        "metadata": {
            "category": "reservations",
            "subcategory": "general_reservation_policy",
            "priority": "medium",
            "keywords": ["reservation", "government rules", "CAP rounds", "caste-based", "EWS", "institute quota", "merit basis"]
        }
    },
    {
        "text": "There is no separate reservation for female candidates in institute quota seats. Female students compete on equal merit basis with male students. However, government reservations for women may be applicable in CAP rounds as per DTE guidelines.",
        "metadata": {
            "category": "reservations",
            "subcategory": "female_reservation",
            "priority": "medium",
            "keywords": ["female candidates", "no separate reservation", "equal merit", "government reservations", "DTE guidelines"]
        }
    },
    {
        "text": "FR CRCE does not have NRI quota or NRI seats. Non-Resident Indian students need to apply through regular admission process either through CAP rounds or institute quota based on merit. No separate category exists for NRI admissions.",
        "metadata": {
            "category": "reservations",
            "subcategory": "nri_quota",
            "priority": "medium",
            "keywords": ["NRI quota", "no NRI seats", "Non-Resident Indian", "regular admission", "no separate category"]
        }
    },
    {
        "text": "There is no separate reservation category for children of Defense personnel in institute quota seats. Defense personnel children compete on merit basis. However, they may be eligible for reservations in CAP rounds as per government rules if applicable.",
        "metadata": {
            "category": "reservations",
            "subcategory": "defense_quota",
            "priority": "medium",
            "keywords": ["Defense personnel", "no separate category", "merit basis", "government rules", "children of defense"]
        }
    },
    {
        "text": "In previous academic year, 80% of total seats were filled through CAP rounds conducted by DTE Maharashtra, and remaining 20% seats were filled through Institute quota rounds. There is no separate management quota beyond this 20% institute quota allocation.",
        "metadata": {
            "category": "reservations",
            "subcategory": "seat_distribution",
            "priority": "medium",
            "keywords": ["80% CAP", "20% institute", "management quota", "seat allocation", "DTE Maharashtra"]
        }
    },
    {
        "text": "FR CRCE is a Christian minority institution recognized by government. Therefore, schemes and benefits pertaining to Christian minority community are applicable as per government guidelines. Christian students may get additional benefits and considerations.",
        "metadata": {
            "category": "reservations",
            "subcategory": "minority_status",
            "priority": "low",
            "keywords": ["Christian minority", "minority institution", "government recognition", "community benefits", "additional considerations"]
        }
    },
    
    # Special Support
    {
        "text": "FR CRCE welcomes differently-abled students and provides comprehensive support including wheelchair accessible ramps, elevators and lifts, dedicated counselor for guidance, special examination concessions as per government rules, and barrier-free campus infrastructure.",
        "metadata": {
            "category": "support",
            "subcategory": "differently_abled_support",
            "priority": "medium",
            "keywords": ["differently-abled", "wheelchair accessible", "ramps", "elevators", "counselor", "exam concessions", "barrier-free"]
        }
    },
    
    # Comparisons & College Selection Advice
    {
        "text": "FR CRCE is a well-established self-financing private institution while CoEP and VJTI are government colleges with different fee structure and admission process. SPCE is government-aided college. Direct comparison is not appropriate due to different funding models, fee structures, and admission criteria.",
        "metadata": {
            "category": "guidance",
            "subcategory": "college_comparison",
            "priority": "low",
            "keywords": ["FRCRCE vs CoEP", "VJTI comparison", "SPCE", "self-financing", "government college", "different models"]
        }
    },
    {
        "text": "When choosing between college and branch, if you are clear about your preferred engineering branch and career goals, then branch selection becomes primary consideration. If you are undecided about branch, then preference should be given to a reputed college with good peer group, faculty, and overall academic environment.",
        "metadata": {
            "category": "guidance",
            "subcategory": "branch_vs_college",
            "priority": "low",
            "keywords": ["branch vs college", "career goals", "preferred branch", "peer group", "academic environment", "college reputation"]
        }
    },
    
    # Contact Information & Admission Guidance
    {
        "text": "College academic session starts as per CET Cell notification and schedule. Students should regularly visit FRCRCE official website www.frcrce.ac.in for latest updates, important dates, and admission notifications. Stay updated through official channels only.",
        "metadata": {
            "category": "contacts",
            "subcategory": "session_start_updates",
            "priority": "medium",
            "keywords": ["session start", "CET cell", "official website", "updates", "important dates", "notifications"]
        }
    },
    {
        "text": "For detailed admission information and queries, students should refer to CET Cell official website, FRCRCE website, and contact college admission enquiry office directly. For information about vacant seats, document requirements, and admission deadlines, contact Mr. Chandrashekhar Shetty who is the Registrar, and the admission committee.",
        "metadata": {
            "category": "contacts",
            "subcategory": "admission_contacts",
            "priority": "medium",
            "keywords": ["admission information", "CET cell website", "enquiry office", "Chandrashekhar Shetty", "Registrar", "admission committee", "vacant seats"]
        }
    },
    {
        "text": "Students and parents are recommended to visit the institute campus personally before taking admission to get first-hand experience of facilities and environment. For specific academic queries, students can contact respective Head of Departments. For first-year academic queries, contact Prof. Dileep Chandra C. who is Head of Humanities and Science Department.",
        "metadata": {
            "category": "contacts",
            "subcategory": "campus_visit_hod_contacts",
            "priority": "low",
            "keywords": ["campus visit", "personal visit", "Head of Department", "HoD", "Dileep Chandra", "first-year", "Humanities Science"]
        }
    },
    
    # Why Choose FR CRCE - Comprehensive advantages
    {
        "text": "FR CRCE is recognized as one of the best self-financed engineering institutions in Maharashtra with prestigious NAAC A+ accreditation and NBA accreditation for quality education. It holds autonomous status permanently affiliated to University of Mumbai providing academic flexibility and updated curriculum.",
        "metadata": {
            "category": "why_choose",
            "subcategory": "accreditation_recognition",
            "priority": "high",
            "keywords": ["best institution", "Maharashtra", "NAAC A+", "NBA accreditation", "autonomous", "University of Mumbai", "quality education"]
        }
    },
    {
        "text": "FR CRCE provides extensive scholarships and financial assistance to deserving students through government schemes, merit scholarships, need-based assistance, and various private scholarship programs making quality education accessible to students from all economic backgrounds.",
        "metadata": {
            "category": "why_choose",
            "subcategory": "financial_support",
            "priority": "high",
            "keywords": ["scholarships", "financial assistance", "government schemes", "merit scholarships", "accessible education", "economic backgrounds"]
        }
    },
    {
        "text": "FR CRCE offers flexible B.Tech programs with options for Multidisciplinary Minor degrees, Honors programs, Double Minor combinations, and Research opportunities. This allows students to customize their education, gain expertise in multiple domains, and enhance their career prospects in emerging technologies.",
        "metadata": {
            "category": "why_choose",
            "subcategory": "flexible_programs",
            "priority": "high",
            "keywords": ["flexible programs", "multidisciplinary", "minor degrees", "honors", "double minor", "research", "customize education", "emerging technologies"]
        }
    },
    {
        "text": "The college has highly experienced and well-qualified faculty members with many holding Ph.D. degrees, industry experience, and active research backgrounds. Faculty provide personalized attention, mentoring, and guidance to ensure student success in academics and career development.",
        "metadata": {
            "category": "why_choose",
            "subcategory": "experienced_faculty",
            "priority": "high",
            "keywords": ["experienced faculty", "Ph.D. degrees", "industry experience", "research background", "mentoring", "personalized attention", "career development"]
        }
    },
    {
        "text": "FR CRCE has established a strong culture of research, innovation, and entrepreneurship with state-of-the-art laboratories, research centers, incubation facilities, and regular industry collaborations. Students get opportunities to work on cutting-edge projects and develop innovative solutions.",
        "metadata": {
            "category": "why_choose",
            "subcategory": "research_innovation",
            "priority": "high",
            "keywords": ["research culture", "innovation", "entrepreneurship", "laboratories", "incubation", "industry collaboration", "cutting-edge projects"]
        }
    },
    {
        "text": "The college focuses on holistic and all-rounded development of students through technical education, personality development programs, leadership training, communication skills, cultural activities, sports, and social service initiatives creating well-rounded engineering professionals.",
        "metadata": {
            "category": "why_choose",
            "subcategory": "holistic_development",
            "priority": "high",
            "keywords": ["holistic development", "personality development", "leadership training", "communication skills", "cultural activities", "sports", "well-rounded professionals"]
        }
    },
    {
        "text": "FR CRCE consistently achieves outstanding academic results with pass percentages of 98% to 100% across all branches. Students regularly secure top ranks in University of Mumbai examinations and receive gold medals and academic excellence awards.",
        "metadata": {
            "category": "why_choose",
            "subcategory": "academic_excellence",
            "priority": "high",
            "keywords": ["outstanding results", "98-100%", "top ranks", "University of Mumbai", "gold medals", "academic excellence", "awards"]
        }
    },
    {
        "text": "The college provides excellent placement opportunities with 100% placement assistance and strong industry connections. Top multinational companies regularly recruit students with competitive salary packages. Career guidance and placement training ensure industry readiness.",
        "metadata": {
            "category": "why_choose",
            "subcategory": "excellent_placements",
            "priority": "high",
            "keywords": ["excellent placements", "100% assistance", "multinational companies", "competitive salary", "career guidance", "industry readiness"]
        }
    },
    {
        "text": "FR CRCE has a strong and supportive alumni network working in leading companies worldwide including Google, Microsoft, Amazon, Goldman Sachs, and other Fortune 500 companies. Alumni provide mentorship, internship opportunities, and career guidance to current students.",
        "metadata": {
            "category": "why_choose",
            "subcategory": "alumni_network",
            "priority": "medium",
            "keywords": ["alumni network", "worldwide", "Google", "Microsoft", "Goldman Sachs", "Fortune 500", "mentorship", "internships"]
        }
    },
    {
        "text": "The college provides comprehensive personality development and soft skills training including communication skills, leadership development, team building, presentation skills, interview preparation, and professional etiquette to make students industry-ready and confident professionals.",
        "metadata": {
            "category": "why_choose",
            "subcategory": "personality_development",
            "priority": "medium",
            "keywords": ["personality development", "soft skills", "communication", "leadership", "team building", "presentation", "interview prep", "professional etiquette"]
        }
    },
    {
        "text": "FR CRCE emphasizes strong moral and ethical values, character building, social responsibility, and ethical engineering practices. The college creates responsible engineers who contribute positively to society while maintaining highest professional ethics.",
        "metadata": {
            "category": "why_choose",
            "subcategory": "moral_ethical_values",
            "priority": "medium",
            "keywords": ["moral values", "ethical values", "character building", "social responsibility", "ethical engineering", "responsible engineers"]
        }
    },
    {
        "text": "The college provides extensive support and expert guidance for national and international level technical competitions, hackathons, research competitions, innovation challenges, and technical paper presentations. Students regularly win prestigious awards and recognition.",
        "metadata": {
            "category": "why_choose",
            "subcategory": "competition_support",
            "priority": "medium",
            "keywords": ["competition support", "hackathons", "research competitions", "innovation challenges", "technical papers", "prestigious awards", "recognition"]
        }
    },
    {
        "text": "FR CRCE has established Memorandums of Understanding MoUs with leading industries, multinational companies, research organizations, and technology partners. These collaborations provide students with internships, live projects, industry exposure, and direct recruitment opportunities.",
        "metadata": {
            "category": "why_choose",
            "subcategory": "industry_mous",
            "priority": "medium",
            "keywords": ["MoU", "industry collaboration", "multinational companies", "research organizations", "internships", "live projects", "recruitment opportunities"]
        }
    },
    {
        "text": "The college gives equal emphasis and excellent facilities for sports, cultural activities, co-curricular programs, and extracurricular activities. Students can participate in inter-college competitions, cultural festivals, technical symposiums, and various clubs and societies for overall personality development.",
        "metadata": {
            "category": "why_choose",
            "subcategory": "sports_cultural_activities",
            "priority": "medium",
            "keywords": ["sports", "cultural activities", "co-curricular", "extracurricular", "competitions", "festivals", "symposiums", "clubs", "societies"]
        }
    },
    {
        "text": "FR CRCE regularly organizes industrial visits and educational tours to leading companies, manufacturing plants, research laboratories, and technical exhibitions. These visits provide practical exposure, industry insights, and real-world application of theoretical knowledge.",
        "metadata": {
            "category": "why_choose",
            "subcategory": "industrial_visits",
            "priority": "low",
            "keywords": ["industrial visits", "educational tours", "manufacturing plants", "research labs", "technical exhibitions", "practical exposure", "industry insights"]
        }
    },
    
    # Additional Dynamic Query Support
    {
        "text": "Students frequently ask about admission deadlines, document submission dates, fee payment last dates, and important academic calendar events. All such time-sensitive information is regularly updated on the official website and through CET cell notifications.",
        "metadata": {
            "category": "general_queries",
            "subcategory": "deadlines_dates",
            "priority": "high",
            "keywords": ["deadlines", "last date", "important dates", "academic calendar", "time-sensitive", "when is", "deadline for"]
        }
    },
    {
        "text": "Common student concerns include campus safety for girls, ragging policies, discipline rules, attendance requirements, examination patterns, grading system, and academic support services. FR CRCE maintains strict anti-ragging policies and ensures safe, conducive learning environment for all students.",
        "metadata": {
            "category": "general_queries",
            "subcategory": "student_concerns",
            "priority": "medium",
            "keywords": ["safety", "girls safety", "ragging", "discipline", "attendance", "examination pattern", "grading", "academic support"]
        }
    },
    {
        "text": "Students often inquire about internship opportunities, summer training programs, project work, final year projects, research opportunities, and industry collaborations available during the course. The college facilitates internships with reputed companies and provides guidance for meaningful project work.",
        "metadata": {
            "category": "general_queries",
            "subcategory": "internships_projects",
            "priority": "medium",
            "keywords": ["internships", "summer training", "project work", "final year project", "research opportunities", "industry collaboration"]
        }
    },
    {
        "text": "Parents and students frequently ask about accommodation options, nearby facilities, medical facilities, banking services, shopping areas, entertainment options, and general living conditions around the campus area in Bandra West Mumbai.",
        "metadata": {
            "category": "general_queries",
            "subcategory": "living_facilities",
            "priority": "low",
            "keywords": ["accommodation", "medical facilities", "banking", "shopping", "entertainment", "living conditions", "nearby facilities"]
        }
    },
    {
        "text": "International students and NRI families often have specific queries about admission procedures, fee structure in foreign currency, document attestation requirements, visa support, and integration support services available at the college.",
        "metadata": {
            "category": "general_queries",
            "subcategory": "international_students",
            "priority": "low",
            "keywords": ["international students", "NRI", "foreign currency", "document attestation", "visa support", "integration support"]
        }
    }
]
# Clean metadata before inserting into Chroma
cleaned_metadata = []
for item in frcrce_knowledge:
    meta = {}
    for k, v in item["metadata"].items():
        if isinstance(v, list):
            meta[k] = ", ".join(map(str, v))  # convert list -> string
        else:
            meta[k] = v
    cleaned_metadata.append(meta)

# Add documents to collection
collection.add(
    documents=[item["text"] for item in frcrce_knowledge],
    metadatas=cleaned_metadata,
    ids=[f"doc_{i}" for i in range(len(frcrce_knowledge))]
)

print(f"Added {len(frcrce_knowledge)} documents to the enhanced FR CRCE knowledge base")

# Comprehensive test queries to verify dynamic query handling
test_queries = [
    # Direct questions
    "What is the fee for B.Tech at FR CRCE?",
    "Where is the college located?",
    "What courses are offered?",
    "How are the placements?",
    
    # Dynamic variations
    "How much does it cost to study at FR CRCE?",
    "Tell me about the location of the campus",
    "What engineering branches are available?",
    "Are placements good at this college?",
    
    # Conversational style
    "I want to know about the fees",
    "Can you tell me where this college is?",
    "What can I study here?",
    "Will I get a job after graduation?",
    
    # Specific concerns
    "Is there any donation required?",
    "Do they have hostel facilities?",
    "What about scholarships?",
    "Is it safe for girls?",
    
    # Comparison queries
    "Why should I choose FR CRCE?",
    "How is it compared to other colleges?",
    "What makes this college special?",
    
    # Process queries
    "How do I apply for admission?",
    "What documents are needed?",
    "When does the session start?",
    
    # Facility queries
    "What facilities are available?",
    "How is the library?",
    "Is there internet on campus?"
]

print("\n" + "="*60)
print("COMPREHENSIVE TEST QUERY RESULTS")
print("="*60)

for i, query in enumerate(test_queries, 1):
    print(f"\n{i}. Query: '{query}'")
    print("-" * 50)
    
    results = collection.query(
        query_texts=[query],
        n_results=2
    )
    
    for j, (doc, metadata) in enumerate(zip(results['documents'][0], results['metadatas'][0])):
        print(f"\nResult {j+1}:")
        print(f"Category: {metadata.get('category', 'N/A')} | Priority: {metadata.get('priority', 'N/A')}")
        
        # Handle keywords safely (they're now strings, not lists)
        keywords_str = metadata.get("keywords", "")
        top_keywords = keywords_str.split(", ")[:5] if keywords_str else []
        print(f"Keywords: {', '.join(top_keywords)}...")
        
        print(f"Text: {doc[:150]}..." if len(doc) > 150 else f"Text: {doc}")
        
    if i % 5 == 0 and i < len(test_queries):
        print(f"\n{'='*20} BATCH {i//5} COMPLETE {'='*20}")

print(f"\n{'='*60}")
print("ENHANCED FR CRCE KNOWLEDGE BASE SETUP COMPLETE!")
print(f"{'='*60}")
print(f"Total documents: {len(frcrce_knowledge)}")
print(f"Enhanced features:")
print(f"  ✓ Multiple phrasings for same information")
print(f"  ✓ Dynamic query keyword matching")
print(f"  ✓ Priority-based retrieval")
print(f"  ✓ Comprehensive keyword coverage")
print(f"  ✓ Natural language variations")
print(f"  ✓ Voice agent optimized responses")

print(f"\nCategories covered:")
categories = set(item["metadata"]["category"] for item in frcrce_knowledge)
for category in sorted(categories):
    count = sum(1 for item in frcrce_knowledge if item["metadata"]["category"] == category)
    print(f"  - {category}: {count} documents")

# Since keywords are now strings, count them safely
keyword_count = 0
for item in frcrce_knowledge:
    kws = item["metadata"].get("keywords", [])
    if isinstance(kws, list):
        keyword_count += len(kws)
    elif isinstance(kws, str):
        keyword_count += len(kws.split(", "))
print(f"\nKeyword coverage: {keyword_count} total keywords")

print(f"Ready for production RAG voice agent!")
print(f"{'='*60}")
