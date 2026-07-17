from app.database.db import engine, SessionLocal
from app.models.models import (Base, Admin, DoctorAccount, User, MedicalHistory,
                                ChatHistory, HealthReport, BMIRecord, Appointment,
                                ConsultationMessage, Prescription, Invoice)
from app.services.pdf_service import generate_health_report, generate_bmi_report
from app.services.consultation_pdf import generate_invoice_pdf, generate_prescription_pdf
from passlib.context import CryptContext
from datetime import datetime, timedelta, date
import uuid, json, os

pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")

def _txn():
    return f"CB{datetime.now().strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:6].upper()}"

def _ago(days=0, hours=0, minutes=0):
    return datetime.now() - timedelta(days=days, hours=hours, minutes=minutes)

# ── Realistic AI conversations ─────────────────────────────────────────────────
CONVERSATIONS = [
    {
        "topic": "fever_cold",
        "messages": [
            ("user",  "I have been having fever since yesterday evening, around 101°F, along with body aches and sore throat."),
            ("model", "I'm sorry to hear that. Fever with body aches and sore throat is commonly associated with viral infections like the flu or common cold.\n\nA few questions to better understand:\n- Do you have a runny or stuffy nose?\n- Any chills or sweating?\n- How's your appetite?\n\nIn the meantime, make sure to stay hydrated, rest well, and monitor your temperature. If it exceeds 103°F, that would warrant urgent medical attention."),
            ("user",  "Yes I have runny nose and chills. Appetite is low. No cough though."),
            ("model", "Based on what you're describing — fever, body aches, sore throat, runny nose, chills, and low appetite — this sounds very much like a viral upper respiratory infection or the flu.\n\n**Self-care suggestions:**\n- Rest as much as possible for the next 48-72 hours\n- Drink warm fluids: water, herbal tea, clear soups\n- Warm saline gargles for sore throat (1/2 tsp salt in warm water)\n- Warm compress on forehead for fever relief\n- Light, easily digestible foods: khichdi, dal, toast\n\n**Monitor for these warning signs:**\n- Fever above 103°F\n- Difficulty breathing\n- Rash appearing on body\n- Symptoms worsening after day 3\n\nMost viral infections resolve in 5-7 days with rest and hydration. This is not a diagnosis — please consult a doctor if symptoms worsen."),
            ("user",  "What foods should I eat and avoid during fever?"),
            ("model", "Great question! Diet plays an important role in recovery.\n\n**Eat these:**\n- Warm dal, khichdi, idli, plain rice\n- Clear vegetable soups and broths\n- Coconut water and fresh fruit juices (no added sugar)\n- Bananas, pomegranate, apples\n- Tulsi (holy basil) tea with ginger and honey\n- Curd/yogurt for probiotics\n\n**Avoid these:**\n- Fried, oily, or spicy foods\n- Dairy (milk, cheese) if you have congestion\n- Cold drinks, ice cream, refrigerated foods\n- Processed or packaged snacks\n- Caffeinated beverages\n- Sugary drinks\n\n**Hydration target:** At least 8-10 glasses of warm or room-temperature water daily. Dehydration can worsen fever significantly.\n\nNote: This is for general guidance only. Always consult a healthcare professional for medical advice."),
            ("user",  "Can I do any yoga or exercise while sick?"),
            ("model", "When you have an active fever, it is strongly advised to **avoid any vigorous exercise or yoga**. Your body needs all its energy for healing.\n\nHowever, once your fever breaks and you feel better (usually after 24-48 hours of being fever-free), you can gradually return:\n\n**Safe during mild recovery:**\n- Gentle stretching in bed\n- Pranayama (breathing exercises): Anulom-Vilom, Nadi Shodhana\n- Short slow walks indoors\n\n**Resume only after full recovery:**\n- Yoga asanas\n- Normal workouts\n\n**The 'neck rule':** If symptoms are above the neck (runny nose, sore throat only) — light activity is okay. If below the neck (body aches, chest, fever) — complete rest.\n\nListen to your body. Pushing yourself while sick prolongs recovery. Rest IS the treatment right now. 🙏"),
        ],
        "report_data": {
            "report_title": "Viral Fever & Upper Respiratory Infection Assessment",
            "summary": "Patient presented with fever (101°F), body aches, sore throat, runny nose, and chills. Symptoms consistent with viral upper respiratory infection or influenza.",
            "main_concerns": [
                {"issue": "Viral Fever", "description": "Temperature of 101°F with accompanying chills and sweating, indicating the body's immune response to a viral pathogen.", "severity": "Moderate"},
                {"issue": "Upper Respiratory Symptoms", "description": "Sore throat, runny nose, and body aches suggesting viral involvement of the upper respiratory tract.", "severity": "Mild"},
                {"issue": "Low Appetite & Fatigue", "description": "Reduced food intake and energy levels due to the systemic viral infection affecting metabolic function.", "severity": "Mild"},
            ],
            "possible_conditions": ["Viral Influenza (Flu)", "Common Cold", "Viral Pharyngitis", "Adenoviral Infection"],
            "suggestions": [
                {"title": "Complete Bed Rest", "detail": "Rest for minimum 48-72 hours. Avoid work or strenuous activity until fever-free for 24 hours."},
                {"title": "Aggressive Hydration", "detail": "Drink 8-10 glasses of warm fluids daily. Coconut water, warm broths, herbal teas."},
                {"title": "Saline Gargle", "detail": "Gargle with warm saline (1/2 tsp salt in 1 cup warm water) 3-4 times daily for sore throat relief."},
                {"title": "Temperature Monitoring", "detail": "Check temperature every 4-6 hours. Seek immediate medical care if fever exceeds 103°F."},
            ],
            "activities_and_yoga": [
                {"name": "Anulom-Vilom (Alternate Nostril Breathing)", "instructions": "Sit comfortably. Close right nostril with thumb, inhale through left. Close left with ring finger, exhale through right. Repeat.", "duration": "5 minutes, twice daily", "benefit": "Clears nasal passages, improves oxygen flow"},
                {"name": "Nadi Shodhana Pranayama", "instructions": "Same as Anulom-Vilom but with 4-count inhale, 4-count hold, 8-count exhale.", "duration": "5 minutes daily", "benefit": "Reduces inflammation, calms the nervous system"},
                {"name": "Gentle Bed Stretches", "instructions": "While lying down, gently stretch arms overhead, then legs. Rotate ankles and wrists.", "duration": "10 minutes morning and evening", "benefit": "Reduces body ache, improves circulation"},
            ],
            "what_to_avoid": [
                {"item": "Fried & Spicy Foods", "reason": "Increases inflammation and digestive load, worsening recovery time"},
                {"item": "Cold Beverages & Ice Cream", "reason": "Aggravates throat inflammation and congestion"},
                {"item": "Strenuous Exercise", "reason": "Diverts energy from immune response, can worsen and prolong illness"},
                {"item": "Caffeine & Alcohol", "reason": "Dehydrating effect counteracts fluid therapy and disrupts sleep"},
                {"item": "Dairy Products", "reason": "Can increase mucus production when congested"},
            ],
            "what_to_follow": [
                {"habit": "Tulsi-Ginger-Honey Tea", "detail": "Boil 5-6 tulsi leaves with 1/2 inch ginger in 2 cups water for 10 minutes. Add honey. Drink 2-3 times daily."},
                {"habit": "Steam Inhalation", "detail": "Inhale steam (plain or with eucalyptus oil) for 10 minutes twice daily to relieve congestion."},
                {"habit": "Sleep 9-10 Hours", "detail": "Extended sleep accelerates immune response and viral clearance significantly."},
                {"habit": "Warm Compress", "detail": "Apply warm damp cloth to forehead and neck for 15 minutes to help reduce fever discomfort."},
            ],
            "diet_plan": {
                "overview": "Anti-inflammatory, easy-to-digest diet focused on hydration and immune support",
                "morning": ["Warm water with lemon and honey", "Tulsi-ginger tea", "Plain idli or toast with dal"],
                "midmorning": ["Coconut water", "Pomegranate or apple"],
                "lunch": ["Moong dal khichdi", "Bottle gourd (lauki) sabzi", "Warm water"],
                "evening": ["Warm vegetable soup or clear broth", "Herbal tea"],
                "dinner": ["Plain rice with dal", "Steamed vegetables", "Small cup of warm milk with turmeric (haldi doodh)"],
                "foods_to_include": ["Tulsi leaves", "Ginger", "Turmeric", "Pomegranate", "Coconut water", "Moong dal", "Bottle gourd"],
                "foods_to_avoid": ["Fried foods", "Cold beverages", "Spicy curries", "Dairy (except warm turmeric milk)", "Processed snacks"],
            },
            "when_to_see_doctor": [
                "Fever above 103°F (39.4°C) not responding to home remedies",
                "Difficulty breathing or chest pain",
                "Symptoms worsen significantly after day 3",
                "High fever in children or elderly (immediate care)",
                "Rash appears on body alongside fever",
            ],
            "disclaimer": "This report is generated by CareBot AI for informational purposes only. It does not constitute a medical diagnosis or treatment plan. Always consult a qualified healthcare professional.",
        }
    },
    {
        "topic": "back_pain",
        "messages": [
            ("user",  "I have been suffering from lower back pain for the past 2 weeks. It gets worse when I sit for long hours at my desk job."),
            ("model", "Lower back pain from prolonged sitting is extremely common, especially in desk jobs. This is often called 'mechanical low back pain' and is usually related to poor posture, muscle strain, or disc-related issues.\n\nCan you tell me more:\n- Where exactly is the pain? (center, left, right, radiating down the leg?)\n- Is it a dull ache or sharp pain?\n- Does it improve when you walk or lie down?\n- Any numbness or tingling in legs?"),
            ("user",  "It's in the center and slightly to the left. Dull ache mostly but sharp when I bend. It gets better when I lie down. No numbness in legs."),
            ("model", "Thank you. Based on your description — central-left lower back pain, dull ache that sharpens with bending, worse with sitting, better when lying down, and no neurological symptoms (numbness/tingling) — this sounds like **muscular low back pain with possible lumbar strain**. The absence of leg symptoms is reassuring and suggests nerve compression is unlikely.\n\n**Immediate relief:**\n- Apply warm compress/heating pad for 15-20 minutes, 3x daily\n- Avoid prolonged sitting — stand and walk every 30-45 minutes\n- Sleep on your side with a pillow between knees\n\n**Posture correction at desk:**\n- Chair height: feet flat on floor, knees at 90°\n- Screen at eye level\n- Use lumbar support cushion\n- Shoulders relaxed, not hunched\n\nThis is general guidance, not a diagnosis. If pain persists beyond 4 weeks or worsens, please see an orthopedic specialist."),
            ("user",  "What exercises and yoga poses can help with lower back pain?"),
            ("model", "These exercises are excellent for desk-job related lower back pain. Do them gently — stop if any movement causes sharp pain.\n\n**Stretches (do 2x daily):**\n\n1. **Child's Pose (Balasana)** — Kneel, sit back on heels, stretch arms forward on floor. Hold 30 seconds. Releases lumbar tension beautifully.\n\n2. **Cat-Cow Stretch** — On all fours, alternate between arching (cow) and rounding (cat) your back. 10 reps slow. Best for morning stiffness.\n\n3. **Knee-to-Chest Stretch** — Lie on back, pull one knee to chest, hold 20 seconds. Repeat other side. Direct lumbar decompression.\n\n4. **Piriformis Stretch** — Cross one ankle over opposite knee (figure-4). Gently press knee down. Hold 30 sec each side.\n\n**Strengthening (3x per week):**\n\n5. **Bird-Dog** — On all fours, extend opposite arm and leg simultaneously. Hold 5 sec, 10 reps each side. Builds core stability.\n\n6. **Glute Bridges** — Lie on back, feet flat, lift hips. Hold 3 sec, lower. 15 reps. Strengthens lower back and glutes.\n\n**Yoga poses to add gradually:** Bhujangasana (Cobra), Setu Bandhasana (Bridge), Shavasana with supported knees.\n\n⚠️ Avoid: Forward bends, heavy lifting, and sit-ups while in pain."),
            ("user",  "What should I eat to reduce inflammation and help my back pain heal faster?"),
            ("model", "Diet has a significant impact on inflammation and tissue healing. Here is a targeted anti-inflammatory diet plan for your back pain:\n\n**Top anti-inflammatory foods for back pain:**\n\n🐟 **Omega-3 rich foods** — Salmon, sardines, flaxseeds, walnuts. Directly reduce inflammatory cytokines.\n\n🫚 **Turmeric (Haldi)** — Curcumin is one of the most potent natural anti-inflammatories. Take with black pepper for 20x better absorption. Golden milk daily is excellent.\n\n🥬 **Leafy greens** — Spinach, methi (fenugreek), palak. Rich in magnesium which relaxes muscle spasms.\n\n🫐 **Berries & citrus** — Antioxidants reduce oxidative stress in inflamed tissues.\n\n🧄 **Ginger & garlic** — Natural COX-2 inhibitors (same mechanism as ibuprofen, naturally).\n\n**What to avoid:**\n- Sugar and refined carbs — pro-inflammatory\n- Processed/packaged foods\n- Trans fats (fried foods, margarine)\n- Excessive red meat\n- Alcohol\n\n**Hydration:** 3-4 liters of water daily. Intervertebral discs are 80% water — dehydration literally shrinks them and worsens pain.\n\nNote: This is nutritional guidance only. Consult a doctor for persistent pain."),
        ],
        "report_data": {
            "report_title": "Chronic Lower Back Pain — Desk Job Related Assessment",
            "summary": "Patient reports 2 weeks of central-left lower back pain worsening with prolonged sitting, improving with rest. Pattern consistent with mechanical lumbar strain, likely postural/occupational in nature. No neurological symptoms present.",
            "main_concerns": [
                {"issue": "Mechanical Lower Back Pain", "description": "Dull central-left lumbar pain that sharpens with bending and prolonged sitting. Classic pattern of muscle strain from desk posture.", "severity": "Moderate"},
                {"issue": "Postural Dysfunction", "description": "Extended desk hours creating sustained lumbar flexion, weakening core stabilizers and overloading lumbar muscles.", "severity": "Moderate"},
            ],
            "possible_conditions": ["Lumbar Muscle Strain", "Lumbar Disc Irritation", "Sacroiliac Joint Dysfunction", "Postural Kyphosis"],
            "suggestions": [
                {"title": "Ergonomic Workstation Setup", "detail": "Chair at height where feet are flat, knees 90°. Screen at eye level. Lumbar support cushion. Keyboard at elbow height."},
                {"title": "Movement Breaks", "detail": "Set a timer — stand and walk for 2-3 minutes every 30-45 minutes of sitting. Non-negotiable."},
                {"title": "Heat Therapy", "detail": "Apply heating pad or warm compress to lower back for 15-20 minutes, 3 times daily, especially before stretching."},
                {"title": "Sleep Position", "detail": "Sleep on side with pillow between knees to maintain spinal alignment. Avoid sleeping on stomach."},
            ],
            "activities_and_yoga": [
                {"name": "Cat-Cow Stretch (Marjaryasana-Bitilasana)", "instructions": "Start on all fours. Inhale, drop belly, lift head and tailbone (Cow). Exhale, round spine, tuck chin to chest (Cat). Flow slowly.", "duration": "10 cycles, twice daily", "benefit": "Lubricates spinal joints, relieves morning stiffness"},
                {"name": "Child's Pose (Balasana)", "instructions": "Kneel with big toes touching. Sit back on heels. Stretch arms forward on mat, forehead down. Breathe deeply.", "duration": "Hold 60 seconds, 3 times daily", "benefit": "Decompresses lumbar spine, releases paraspinal muscles"},
                {"name": "Glute Bridge", "instructions": "Lie on back, knees bent, feet flat. Press feet into floor, lift hips until body forms straight line from knees to shoulders. Squeeze glutes at top.", "duration": "3 sets of 15 reps daily", "benefit": "Strengthens posterior chain, reduces lumbar load"},
                {"name": "Bird-Dog", "instructions": "On all fours, extend right arm and left leg simultaneously. Keep back flat. Hold 5 seconds. Alternate sides.", "duration": "3 sets of 10 reps each side", "benefit": "Core stabilization, reduces spinal instability"},
                {"name": "Cobra Pose (Bhujangasana)", "instructions": "Lie face down, palms under shoulders. Gently lift chest off floor using back muscles (not arms). Hold 20 seconds.", "duration": "5 reps, twice daily", "benefit": "Strengthens lumbar extensors, counteracts flexion posture"},
            ],
            "what_to_avoid": [
                {"item": "Prolonged Sitting (>45 min)", "reason": "Increases intradiscal pressure and compresses lumbar muscles, the primary cause of your pain"},
                {"item": "Forward Bending without Knee Bend", "reason": "Creates enormous leverage force on lumbar discs — can worsen strain significantly"},
                {"item": "Heavy Lifting", "reason": "Avoid all lifting >5kg until pain resolves completely"},
                {"item": "High-Heeled Footwear", "reason": "Shifts center of gravity forward, increasing lumbar lordosis and strain"},
                {"item": "Soft/Sagging Mattress", "reason": "Lacks spinal support during sleep, worsening recovery"},
            ],
            "what_to_follow": [
                {"habit": "Daily 20-Minute Walk", "detail": "Flat-surface walking is the single best exercise for back pain. Maintain upright posture. Start slow."},
                {"habit": "Golden Milk (Haldi Doodh)", "detail": "Warm milk with 1 tsp turmeric, pinch of black pepper, and honey. Daily before bed for anti-inflammatory effect."},
                {"habit": "Core Strengthening Routine", "detail": "Plank, bird-dog, and bridge 5 days per week. Strong core = protected lower back."},
                {"habit": "Mindful Sitting Posture", "detail": "Set phone alarm every 30 min as posture check reminder during work hours."},
            ],
            "diet_plan": {
                "overview": "Anti-inflammatory diet focused on omega-3 fatty acids, magnesium, and curcumin for tissue repair and pain reduction",
                "morning": ["Warm turmeric milk or golden milk", "Overnight soaked walnuts and almonds (5 each)", "Egg white omelette with spinach or oats with flaxseeds"],
                "midmorning": ["Fresh fruit — papaya or berries", "Green tea"],
                "lunch": ["Brown rice or roti with dal", "Palak (spinach) sabzi", "Cucumber-tomato salad", "Curd"],
                "evening": ["Ginger-tulsi tea", "Handful of mixed nuts"],
                "dinner": ["Grilled fish or tofu with vegetables", "Or: Moong dal with roti", "Warm soup"],
                "foods_to_include": ["Turmeric with black pepper", "Fatty fish (salmon, sardines)", "Walnuts and flaxseeds", "Spinach and leafy greens", "Ginger and garlic", "Berries"],
                "foods_to_avoid": ["Sugar and sweets", "Fried and processed foods", "Excessive red meat", "Alcohol", "Refined white flour products"],
            },
            "when_to_see_doctor": [
                "Pain radiates down the leg (sciatica pattern)",
                "Numbness or tingling in legs or feet",
                "Bladder or bowel control issues (emergency — go immediately)",
                "Pain worsens despite 4 weeks of home care",
                "History of cancer, osteoporosis, or recent trauma",
            ],
            "disclaimer": "This report is generated by CareBot AI for informational purposes only and does not constitute medical diagnosis or treatment. Always consult a qualified healthcare professional.",
        }
    },
    {
        "topic": "anxiety_stress",
        "messages": [
            ("user",  "I have been feeling very anxious and stressed lately. My mind races at night and I cannot sleep properly. Work pressure is very high."),
            ("model", "I hear you — what you're describing sounds really exhausting. Racing thoughts at night and stress-disrupted sleep is one of the most common yet debilitating combinations.\n\nA few things to understand better:\n- How long has this been going on?\n- Are you getting any sleep at all, or waking frequently?\n- Do you feel anxious during the day too, or mainly at night?\n- Any physical symptoms like chest tightness, headaches, or stomach issues?"),
            ("user",  "It has been about 3 weeks. I get maybe 4-5 hours of broken sleep. Anxious during day too especially before meetings. No chest pain but I do get headaches."),
            ("model", "Thank you for sharing that. What you are experiencing sounds like work-related anxiety with significant sleep disruption — a very real and increasingly common condition.\n\n3 weeks of sustained anxiety with 4-5 hours of broken sleep is already affecting your cognitive function, mood, and physical health. This is not something to push through — it needs attention.\n\n**Right now, tonight:**\n\n🌬️ **4-7-8 Breathing technique:**\nInhale through nose for 4 counts → Hold for 7 → Exhale slowly through mouth for 8. Repeat 4 cycles. This activates the parasympathetic nervous system and is clinically proven to reduce acute anxiety within minutes.\n\n📵 **Phone-free 60 minutes before bed** — Blue light suppresses melatonin and your anxious brain needs clear deactivation time.\n\n📓 **Brain dump journaling** — Before bed, write every worry and tomorrow's task list. Your mind will stop cycling through them because they're 'parked on paper.'\n\nThis is not a diagnosis of any mental health condition. These are wellness tools only. If symptoms persist or worsen, please speak with a mental health professional."),
            ("user",  "What relaxation techniques can help me during the day when I feel anxious before a meeting?"),
            ("model", "Great that you asked — having in-the-moment tools for pre-meeting anxiety is very practical.\n\n**Techniques you can use at your desk (30-120 seconds each):**\n\n**1. Box Breathing (used by military and surgeons)**\nInhale 4 sec → Hold 4 → Exhale 4 → Hold 4. Repeat 4 cycles. Immediately calms the stress response.\n\n**2. 5-4-3-2-1 Grounding**\nName 5 things you see → 4 you can touch → 3 you hear → 2 you smell → 1 you taste. Breaks the anxiety spiral by forcing present-moment focus.\n\n**3. Cold Water on Wrists & Face**\nWash face or run cold water on wrists for 30 seconds. Activates the dive reflex — lowers heart rate rapidly.\n\n**4. Power Posture (2 minutes)**\nStand tall, shoulders back, chin up. Studies show this reduces cortisol and increases confidence before high-stakes situations.\n\n**5. Nadi Shodhana (Alternate Nostril Breathing)**\nClose right nostril, inhale left. Close left, exhale right. 5 cycles. Balances the nervous system.\n\n**Pre-meeting habit:** Arrive 5 minutes early. Sit quietly, do box breathing, review your first sentence. Anxiety spikes from uncertainty — having a clear starting point helps enormously.\n\nRemember: anxiety before important events is normal and even performance-enhancing in small doses. You are not broken. 💙"),
        ],
        "report_data": {
            "report_title": "Work-Related Anxiety & Sleep Disruption Assessment",
            "summary": "Patient reports 3 weeks of sustained anxiety, pre-meeting nervousness, racing thoughts, and broken sleep (4-5 hours). Pattern consistent with work-related stress disorder with secondary insomnia. No acute psychiatric emergency.",
            "main_concerns": [
                {"issue": "Work-Related Anxiety", "description": "Persistent daytime anxiety heightened before meetings and deadlines, indicating performance anxiety with generalized anxiety components.", "severity": "Moderate"},
                {"issue": "Sleep Disruption (Insomnia)", "description": "Only 4-5 hours of broken sleep nightly for 3 weeks. Chronic sleep deprivation significantly impairs cognitive function, emotional regulation, and immune response.", "severity": "Needs Attention"},
                {"issue": "Tension Headaches", "description": "Recurring headaches likely caused by muscle tension from sustained stress response and sleep deprivation.", "severity": "Mild"},
            ],
            "possible_conditions": ["Adjustment Disorder with Anxiety", "Work-Related Stress Disorder", "Generalized Anxiety Disorder (mild)", "Secondary Insomnia"],
            "suggestions": [
                {"title": "Establish a Sleep Ritual", "detail": "Fixed bedtime and wake time daily (including weekends). No screens 60 min before bed. Dim lights after 9 PM."},
                {"title": "Therapy / Counseling", "detail": "Consider 4-6 sessions of Cognitive Behavioral Therapy for Insomnia (CBT-I) — the gold standard, more effective than medication."},
                {"title": "Work Boundary Setting", "detail": "Define a clear end-of-work time. No work emails/Slack after that hour. Physical transition ritual (change clothes, walk) to signal brain that work is over."},
                {"title": "Daily Anxiety Journaling", "detail": "Morning: write 3 things causing anxiety. Evening: write what you handled well. This builds metacognitive awareness of anxiety triggers."},
            ],
            "activities_and_yoga": [
                {"name": "4-7-8 Breathing", "instructions": "Inhale through nose for 4 counts. Hold breath for 7 counts. Exhale completely through mouth for 8 counts. This is one cycle.", "duration": "4 cycles, before bed and when anxious", "benefit": "Activates parasympathetic nervous system, reduces anxiety within 2 minutes"},
                {"name": "Yoga Nidra (Yogic Sleep)", "instructions": "Use a guided audio recording. Lie flat in Shavasana. Follow body scan and breath awareness for 20-30 minutes.", "duration": "Daily before sleep", "benefit": "30 min of Yoga Nidra equals 3 hours of regular sleep neurologically"},
                {"name": "Nadi Shodhana Pranayama", "instructions": "Sit comfortably. Close right nostril, inhale left for 4 counts. Close left, exhale right for 8 counts. Alternate.", "duration": "10 minutes morning and evening", "benefit": "Directly balances left-right brain hemispheres, reduces cortisol"},
                {"name": "Evening Walk (Mindful)", "instructions": "30-minute walk without phone. Focus only on physical sensations — feet touching ground, air temperature, sounds around you.", "duration": "Daily, preferably after work", "benefit": "Cortisol reduction, natural sleep hormone reset, mental decompression"},
            ],
            "what_to_avoid": [
                {"item": "Caffeine after 2 PM", "reason": "Caffeine has a 5-6 hour half-life. Afternoon coffee keeps cortisol elevated and directly causes the racing mind at night"},
                {"item": "News and Social Media Before Bed", "reason": "Activates threat-detection pathways in the brain, the opposite of what's needed for sleep"},
                {"item": "Alcohol as a Sleep Aid", "reason": "While it may help you fall asleep, it dramatically reduces REM sleep quality and worsens anxiety the next day"},
                {"item": "Skipping Meals", "reason": "Blood sugar crashes trigger cortisol release, worsening anxiety symptoms significantly"},
                {"item": "Overcommitting to Tasks", "reason": "The pressure of an overloaded to-do list is a primary driver of your current anxiety cycle"},
            ],
            "what_to_follow": [
                {"habit": "Morning Sunlight (10-15 min)", "detail": "Step outside within 30 minutes of waking. Sunlight exposure sets your circadian rhythm and boosts serotonin — nature's antidepressant."},
                {"habit": "Ashwagandha (KSM-66)", "detail": "300-600mg ashwagandha extract daily has clinical evidence for reducing cortisol by 28% in stressed adults. Consult doctor before starting."},
                {"habit": "Gratitude Practice", "detail": "Write 3 specific things you are grateful for each evening. Scientifically proven to rewire the brain toward positive emotional bias within 3 weeks."},
                {"habit": "Single-Tasking", "detail": "Work on one task at a time. Close other tabs. Put phone in another room. Multitasking increases cortisol by 40%."},
            ],
            "diet_plan": {
                "overview": "Nervous system supportive diet rich in magnesium, B vitamins, and tryptophan to naturally regulate cortisol and promote serotonin production",
                "morning": ["Warm water with lemon", "Oats with banana and pumpkin seeds (magnesium-rich)", "1 cup green tea (not coffee)"],
                "midmorning": ["Handful of almonds and dark chocolate (70%+)", "Chamomile or ashwagandha tea"],
                "lunch": ["Brown rice with rajma or chickpeas", "Spinach sabzi", "Curd (probiotic for gut-brain axis)", "Salad"],
                "evening": ["Chamomile or lavender tea", "Fruits — banana or kiwi (natural melatonin)"],
                "dinner": ["Light meal — dal soup with roti", "Warm turmeric milk before bed", "Avoid heavy, oily dinner"],
                "foods_to_include": ["Magnesium: pumpkin seeds, spinach, dark chocolate", "B6/B12: eggs, chickpeas, bananas", "Omega-3: walnuts, flaxseeds", "Tryptophan: milk, curd, turkey"],
                "foods_to_avoid": ["Caffeine (limit to 1 cup before noon)", "Alcohol", "Refined sugar", "Ultra-processed foods", "Excess salt"],
            },
            "when_to_see_doctor": [
                "Anxiety interferes with work or daily functioning for more than 4 weeks",
                "Panic attacks (sudden intense fear, heart racing, difficulty breathing)",
                "Thoughts of harming yourself — seek immediate help",
                "Sleep deprivation causes impaired driving or work performance",
                "Symptoms worsen despite consistent self-care for 2 weeks",
            ],
            "disclaimer": "This report is generated by CareBot AI for informational and wellness purposes only. It does not constitute mental health diagnosis or treatment. If you are struggling, please speak with a qualified mental health professional.",
        }
    },
]

PRESCRIPTION_DATA = [
    {
        "diagnosis": "Viral Upper Respiratory Tract Infection (URTI) with mild fever",
        "medicines": [
            {"name": "Paracetamol 500mg", "dosage": "1 tablet", "frequency": "3 times daily after meals", "duration": "5 days"},
            {"name": "Cetirizine 10mg", "dosage": "1 tablet", "frequency": "Once daily at night", "duration": "5 days"},
            {"name": "Vitamin C 500mg", "dosage": "1 tablet", "frequency": "Twice daily", "duration": "7 days"},
            {"name": "ORS Sachet", "dosage": "1 sachet in 1L water", "frequency": "Sip throughout the day", "duration": "3 days or until hydrated"},
        ],
        "instructions": "Complete bed rest for 2-3 days. Drink minimum 3 litres of warm fluids daily. Warm saline gargle 3-4 times daily for throat relief. Monitor temperature every 6 hours. Avoid cold foods and beverages. Return immediately if temperature exceeds 103°F, difficulty breathing, or rash appears.",
        "follow_up": "After 5 days or sooner if symptoms worsen"
    },
    {
        "diagnosis": "Mechanical Lumbar Strain with Postural Dysfunction",
        "medicines": [
            {"name": "Diclofenac Sodium 50mg", "dosage": "1 tablet", "frequency": "Twice daily after meals", "duration": "7 days"},
            {"name": "Muscle Relaxant (Methocarbamol 500mg)", "dosage": "1 tablet", "frequency": "Once at night", "duration": "5 days"},
            {"name": "Vitamin D3 60000 IU", "dosage": "1 sachet in water", "frequency": "Once weekly", "duration": "8 weeks"},
            {"name": "Calcium + Magnesium Supplement", "dosage": "1 tablet", "frequency": "Once daily with meals", "duration": "30 days"},
        ],
        "instructions": "Apply warm compress to lower back 3 times daily for 15-20 minutes. Perform prescribed physiotherapy exercises daily. Avoid lifting anything above 5kg. Do NOT sit for more than 45 minutes at a stretch — use a timer. Sleep on firm mattress, side-lying with pillow between knees. Stop NSAIDs if stomach upset occurs and inform doctor.",
        "follow_up": "After 2 weeks. Book physiotherapy assessment if no improvement in 7 days."
    },
    {
        "diagnosis": "Work-Related Anxiety Disorder with Secondary Insomnia",
        "medicines": [
            {"name": "Ashwagandha KSM-66 300mg", "dosage": "1 capsule", "frequency": "Twice daily (morning and night)", "duration": "30 days"},
            {"name": "Melatonin 3mg", "dosage": "1 tablet", "frequency": "30 minutes before sleep", "duration": "14 days"},
            {"name": "Vitamin B Complex", "dosage": "1 tablet", "frequency": "Once daily with breakfast", "duration": "30 days"},
        ],
        "instructions": "Follow CBT-I sleep hygiene protocol strictly: fixed bed/wake time daily, no screens 1 hour before bed, limit caffeine to before 2 PM. Practice 4-7-8 breathing daily. Consider 4-6 sessions with a psychologist (CBT therapy). Keep anxiety journal. Limit news consumption. If anxiety significantly worsens or suicidal thoughts arise, seek immediate psychiatric help.",
        "follow_up": "After 4 weeks. Refer to psychiatrist if no improvement."
    },
]


def seed_users(db):
    users_data = [
        {
            "full_name": "Arjun Verma", "email": "arjun@demo.com", "phone": "9876543210",
            "dob": date(1992, 6, 15), "gender": "Male", "password": "Demo@123",
            "allergies": "Penicillin", "chronic_conditions": "Mild hypertension",
            "surgeries": "", "medications": "Amlodipine 5mg", "family_history": "Father: Diabetes, Mother: Hypertension",
        },
        {
            "full_name": "Priya Sharma", "email": "priya@demo.com", "phone": "9876541234",
            "dob": date(1988, 3, 22), "gender": "Female", "password": "Demo@123",
            "allergies": "Dust mites, Pollen", "chronic_conditions": "Asthma (mild, controlled)",
            "surgeries": "Appendectomy 2015", "medications": "Salbutamol inhaler (as needed)", "family_history": "Mother: Thyroid disorder",
        },
        {
            "full_name": "Rahul Singh", "email": "rahul@demo.com", "phone": "9988776655",
            "dob": date(1995, 11, 8), "gender": "Male", "password": "Demo@123",
            "allergies": "", "chronic_conditions": "",
            "surgeries": "", "medications": "", "family_history": "Grandfather: Heart disease",
        },
    ]

    users = []
    for ud in users_data:
        if db.query(User).filter(User.email == ud["email"]).first():
            users.append(db.query(User).filter(User.email == ud["email"]).first())
            continue
        u = User(
            full_name=ud["full_name"], email=ud["email"], phone=ud["phone"],
            dob=ud["dob"], gender=ud["gender"],
            password_hash=pwd_ctx.hash(ud["password"]),
            created_at=_ago(days=45)
        )
        db.add(u); db.flush()
        db.add(MedicalHistory(
            user_id=u.id, allergies=ud["allergies"],
            chronic_conditions=ud["chronic_conditions"],
            surgeries=ud["surgeries"], medications=ud["medications"],
            family_history=ud["family_history"]
        ))
        users.append(u)
        print(f"✓ User: {ud['email']} / {ud['password']}")
    db.commit()
    return users


def seed_bmi(db, users):
    bmi_entries = [
        # Arjun - slightly overweight, improving
        [
            (175, 82, _ago(days=60)), (175, 80, _ago(days=30)), (175, 78, _ago(days=5)),
        ],
        # Priya - normal weight, stable
        [
            (162, 58, _ago(days=45)), (162, 57, _ago(days=15)),
        ],
        # Rahul - underweight, gaining
        [
            (180, 62, _ago(days=30)), (180, 64, _ago(days=7)),
        ],
    ]

    for user, entries in zip(users, bmi_entries):
        for height, weight, ts in entries:
            if db.query(BMIRecord).filter(BMIRecord.user_id == user.id, BMIRecord.height == height, BMIRecord.weight == weight).first():
                continue
            bmi = round(weight / ((height / 100) ** 2), 1)
            if bmi < 18.5: cat = "Underweight"
            elif bmi < 25: cat = "Normal Weight"
            elif bmi < 30: cat = "Overweight"
            else: cat = "Obese"
            r = BMIRecord(user_id=user.id, height=height, weight=weight, bmi=bmi, category=cat, created_at=ts)
            db.add(r)
    db.commit()
    print("✓ BMI records seeded")


def seed_ai_chats_and_reports(db, users):
    for i, (user, conv) in enumerate(zip(users, CONVERSATIONS)):
        session_id = str(uuid.uuid4())
        existing = db.query(ChatHistory).filter(ChatHistory.user_id == user.id, ChatHistory.session_id == session_id).first()
        if existing:
            continue

        msgs = conv["messages"]
        for idx, (role, content) in enumerate(msgs):
            db.add(ChatHistory(
                user_id=user.id, session_id=session_id,
                user_message=content if role == "user" else "[system]",
                ai_response=content if role == "model" else msgs[idx+1][1] if idx+1 < len(msgs) and msgs[idx+1][0] == "model" else "",
                message_index=idx // 2,
                timestamp=_ago(days=20 - i*5, hours=idx)
            ))

        db.flush()

        # Generate health report PDF
        report_data = conv["report_data"]
        try:
            pdf_file = generate_health_report(user, report_data, session_id)
            report = HealthReport(
                user_id=user.id, session_id=session_id,
                report_path=pdf_file,
                report_title=report_data["report_title"],
                created_at=_ago(days=19 - i*5)
            )
            db.add(report)
            print(f"✓ AI chat + report for {user.full_name}: {pdf_file}")
        except Exception as e:
            print(f"  ⚠ Report PDF skipped for {user.full_name}: {e}")

    db.commit()


def seed_appointments(db, users, doctors):
    appt_scenarios = [
        # Arjun — completed consultation with Dr. Sharma (General Physician), fever
        {
            "user_idx": 0, "doctor_idx": 0,
            "symptoms": "Fever since 2 days, body aches, sore throat. Temperature around 101°F.",
            "status": "completed",
            "days_ago": 15,
            "rx_idx": 0,
            "chat": [
                ("doctor", "Hello Arjun! I've reviewed your symptoms. Fever with body aches and sore throat — can you tell me if you have any runny nose or cough as well?"),
                ("patient", "Yes doctor, I have a runny nose. No cough but I feel very weak and my appetite is very low."),
                ("doctor", "Understood. Based on what you're describing, this looks like a viral upper respiratory infection, likely influenza. Your symptoms and the pattern are classic. I'm going to prescribe medication for symptomatic relief.\n\nKey things to do:\n1. Complete bed rest for 3 days\n2. Drink at least 3 litres of warm fluids daily\n3. Warm saline gargle for the throat\n4. Monitor temperature regularly\n\nPlease take the medicines I'll prescribe with food. The fever should come down within 24-48 hours."),
                ("patient", "Thank you doctor. Should I get any tests done?"),
                ("doctor", "At this stage, no tests are needed. Viral infections don't respond to antibiotics and blood tests are typically normal. Rest and hydration are the real treatment. However, if the fever exceeds 103°F, doesn't improve in 4 days, or you develop rash or difficulty breathing — go to a hospital immediately. I'll issue your prescription now. Take care!"),
            ]
        },
        # Priya — completed consultation with Dr. Kumar (Orthopedic), back pain
        {
            "user_idx": 1, "doctor_idx": 2,
            "symptoms": "Lower back pain for 2 weeks. Worsens with sitting. Work from home since 1 year.",
            "status": "completed",
            "days_ago": 8,
            "rx_idx": 1,
            "chat": [
                ("doctor", "Hello Priya! I can see you've been having lower back pain for 2 weeks. Working from home definitely contributes to this. Can you tell me — does the pain radiate down your leg at all, or stay localized to the lower back?"),
                ("patient", "It stays in the lower back, slightly to the left. No pain in legs. It's a dull ache mostly but sharp when I try to bend."),
                ("doctor", "Good — the absence of leg pain is an important positive sign, suggesting no nerve involvement. This is classic mechanical low back pain from postural strain. Very common in work-from-home settings.\n\nI'll prescribe a short course of anti-inflammatory medication and a muscle relaxant for nights. But medication is only 20% of the treatment — the physiotherapy exercises are the real cure.\n\nImmediate changes: set an alarm to stand every 30 minutes, use a chair with lumbar support, screen at eye level. Do the Cat-Cow and Child's Pose stretches I'll describe."),
                ("patient", "Should I get an MRI done doctor?"),
                ("doctor", "Not at this stage. MRI is needed only if symptoms don't improve in 4-6 weeks, OR if you develop leg pain, numbness, or weakness. For acute mechanical pain of 2 weeks, physiotherapy and activity modification have better outcomes than imaging.\n\nStart the exercises gently, take the medicines with food, apply heat 3 times daily, and follow up in 2 weeks. If pain significantly worsens, go to a hospital. I'm issuing your prescription now — please follow the instructions carefully!"),
            ]
        },
        # Rahul — active consultation with Dr. Singh (Psychiatrist), anxiety
        {
            "user_idx": 2, "doctor_idx": 4,
            "symptoms": "Anxiety and stress. Cannot sleep. Work pressure. Racing thoughts at night.",
            "status": "active",
            "days_ago": 1,
            "rx_idx": None,
            "chat": [
                ("doctor", "Hello Rahul, I'm Dr. Vikram Singh. I've reviewed your concern about anxiety and sleep issues. First — thank you for reaching out. It takes courage to address mental health. Can you tell me how long this has been going on and if there were any specific triggers?"),
                ("patient", "It's been about 3-4 weeks. My workplace changed management and the new manager is very demanding. I have deadlines every day and feel like I'm always behind. I lie down at night but my mind just keeps going through everything."),
                ("doctor", "That makes complete sense. A significant change in workplace dynamics — especially with demanding management — is a recognised stressor that can trigger exactly what you're describing: hyperactivation of the stress response, which prevents the brain from switching off at night.\n\nWhat you're experiencing is called 'stress-induced insomnia' and it's very common and very treatable. You're not developing a mental illness — you're having a normal reaction to an abnormal amount of sustained pressure.\n\nCan you tell me: on a scale of 1-10, how would you rate your anxiety during the day?"),
                ("patient", "Maybe a 7 during the day, and 9 at night when trying to sleep. I feel my heart beat fast sometimes."),
                ("doctor", "Thank you for that. A 7-9 is significant and definitely worth addressing proactively — you're right to seek help now rather than letting it escalate.\n\nThe heart racing you mention is likely palpitations from anxiety — your body producing adrenaline when it perceives threat. Uncomfortable but not dangerous in the absence of cardiac history.\n\nI'm going to recommend a combination approach: evidence-based supplements to support your nervous system, specific breathing techniques proven in clinical trials, and sleep hygiene protocol. I'll issue you a detailed prescription and instructions shortly."),
            ]
        },
        # Arjun again — paid (awaiting doctor), different doctor
        {
            "user_idx": 0, "doctor_idx": 1,
            "symptoms": "Occasional chest tightness and shortness of breath after climbing stairs. I have mild hypertension.",
            "status": "paid",
            "days_ago": 0,
            "rx_idx": None,
            "chat": []
        },
    ]

    created_appts = []
    for scenario in appt_scenarios:
        user = users[scenario["user_idx"]]
        doctor = doctors[scenario["doctor_idx"]]
        platform_fee = round(doctor.fee * 0.10)
        txn = _txn()

        existing = db.query(Appointment).filter(
            Appointment.user_id == user.id,
            Appointment.doctor_id == doctor.id,
            Appointment.symptoms_note == scenario["symptoms"][:50]
        ).first()
        if existing:
            created_appts.append(existing)
            continue

        appt = Appointment(
            user_id=user.id, doctor_id=doctor.id,
            status=scenario["status"],
            txn_id=txn, fee_paid=doctor.fee, platform_fee=platform_fee,
            symptoms_note=scenario["symptoms"],
            created_at=_ago(days=scenario["days_ago"], hours=3)
        )
        db.add(appt); db.flush()

        # Invoice PDF
        try:
            inv_pdf = generate_invoice_pdf(appt, user, doctor)
            db.add(Invoice(
                appointment_id=appt.id, txn_id=txn,
                amount=doctor.fee, platform_fee=platform_fee,
                total=doctor.fee + platform_fee, pdf_path=inv_pdf,
                created_at=_ago(days=scenario["days_ago"], hours=3)
            ))
        except Exception as e:
            print(f"  ⚠ Invoice PDF skipped: {e}")

        # Chat messages
        for j, (role, msg) in enumerate(scenario["chat"]):
            db.add(ConsultationMessage(
                appointment_id=appt.id, sender_role=role, message=msg,
                timestamp=_ago(days=scenario["days_ago"], hours=2, minutes=j*8)
            ))

        # Prescription for completed ones
        if scenario["status"] == "completed" and scenario["rx_idx"] is not None:
            rxd = PRESCRIPTION_DATA[scenario["rx_idx"]]
            pres = Prescription(
                appointment_id=appt.id,
                diagnosis=rxd["diagnosis"],
                medicines=json.dumps(rxd["medicines"]),
                instructions=rxd["instructions"],
                follow_up=rxd["follow_up"],
                created_at=_ago(days=scenario["days_ago"])
            )
            db.add(pres); db.flush()
            try:
                rx_pdf = generate_prescription_pdf(appt, pres, user, doctor)
                pres.pdf_path = rx_pdf
                print(f"✓ Prescription PDF: {rx_pdf}")
            except Exception as e:
                print(f"  ⚠ Prescription PDF skipped: {e}")

        created_appts.append(appt)
        print(f"✓ Appointment: {user.full_name} → Dr. {doctor.full_name} [{scenario['status']}]")

    db.commit()
    return created_appts


def init_db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    print("\n━━━━ CareBot Database Initialization ━━━━\n")

    # Admin
    if not db.query(Admin).filter(Admin.email == "admin@carebot.com").first():
        db.add(Admin(username="admin", email="admin@carebot.com", password_hash=pwd_ctx.hash("Admin@123")))
        print("✓ Admin: admin@carebot.com / Admin@123")

    # Doctors
    sample_doctors = [
        {"full_name": "Rajesh Sharma",  "email": "dr.sharma@carebot.com", "specialty": "General Physician",
         "qualification": "MBBS, MD", "experience_years": 12, "fee": 400, "rating": 4.8,
         "bio": "Experienced general physician with expertise in infectious diseases, chronic illness management, and preventive healthcare."},
        {"full_name": "Priya Mehta",    "email": "dr.mehta@carebot.com",  "specialty": "Cardiologist",
         "qualification": "MBBS, MD, DM Cardiology", "experience_years": 15, "fee": 800, "rating": 4.9,
         "bio": "Specialist in heart disease, hypertension, and cardiovascular health with advanced training in interventional cardiology."},
        {"full_name": "Arun Kumar",     "email": "dr.kumar@carebot.com",  "specialty": "Orthopedic",
         "qualification": "MBBS, MS Orthopedics", "experience_years": 10, "fee": 600, "rating": 4.7,
         "bio": "Expert in joint pain, sports injuries, back pain, and bone health. Specialized in non-surgical treatment approaches."},
        {"full_name": "Sneha Patel",    "email": "dr.patel@carebot.com",  "specialty": "Dermatologist",
         "qualification": "MBBS, MD Dermatology", "experience_years": 8,  "fee": 500, "rating": 4.6,
         "bio": "Skin specialist with expertise in acne, eczema, psoriasis, hair loss, and cosmetic dermatology."},
        {"full_name": "Vikram Singh",   "email": "dr.singh@carebot.com",  "specialty": "Psychiatrist",
         "qualification": "MBBS, MD Psychiatry", "experience_years": 11, "fee": 700, "rating": 4.8,
         "bio": "Mental health specialist focused on anxiety, depression, stress management, and cognitive behavioral therapy."},
        {"full_name": "Anitha Nair",    "email": "dr.nair@carebot.com",   "specialty": "Pediatrician",
         "qualification": "MBBS, MD Pediatrics", "experience_years": 9,  "fee": 450, "rating": 4.9,
         "bio": "Child health specialist with expertise in growth and development, childhood diseases, and adolescent health."},
    ]
    doctors = []
    for d in sample_doctors:
        existing = db.query(DoctorAccount).filter(DoctorAccount.email == d["email"]).first()
        if existing:
            doctors.append(existing)
        else:
            doc = DoctorAccount(password_hash=pwd_ctx.hash("Doctor@123"), available="Yes", **d)
            db.add(doc); db.flush()
            doctors.append(doc)
            print(f"✓ Doctor: {d['email']} / Doctor@123")
    db.commit()

    # Seed users
    print("\n── Demo Users ──")
    users = seed_users(db)

    # BMI records
    print("\n── BMI Records ──")
    seed_bmi(db, users)

    # AI chats + report PDFs
    print("\n── AI Conversations & Reports ──")
    seed_ai_chats_and_reports(db, users)

    # Appointments, invoices, prescriptions
    print("\n── Appointments & Consultations ──")
    seed_appointments(db, users, doctors)

    db.close()

    print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("  ✅ CareBot fully initialized with demo data")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("\n  👤 DEMO USERS (password: Demo@123)")
    print("     arjun@demo.com  — Arjun Verma  (hypertension, completed consult, AI reports)")
    print("     priya@demo.com  — Priya Sharma  (asthma history, back pain consult, BMI)")
    print("     rahul@demo.com  — Rahul Singh   (anxiety consult in progress)")
    print("\n  👨‍⚕️ DOCTORS (password: Doctor@123)")
    print("     dr.sharma@carebot.com — General Physician")
    print("     dr.mehta@carebot.com  — Cardiologist")
    print("     dr.kumar@carebot.com  — Orthopedic")
    print("     dr.patel@carebot.com  — Dermatologist")
    print("     dr.singh@carebot.com  — Psychiatrist")
    print("     dr.nair@carebot.com   — Pediatrician")
    print("\n  🛡️ ADMIN")
    print("     admin@carebot.com / Admin@123")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")


if __name__ == "__main__":
    init_db()