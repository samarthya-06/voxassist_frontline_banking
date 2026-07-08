"""AI Orchestrator — Sarvam STT/TTS, translation, entities, compliance, summarization."""

import asyncio
import base64
import io
import json
import logging
import re
from datetime import datetime
from uuid import uuid4


import httpx

from ..core.config import settings
from ..models.forms import (
    FORM_REGISTRY,
    FormDefinition,
    FormSession,
    FormType,
    get_all_form_types,
    get_form_definition,
)
from ..models.session import ComplianceAlert, SentimentResult, SopResult, TranscriptItem
from .rag_service import rag_service

logger = logging.getLogger(__name__)

# ── Sarvam API base ──────────────────────────────────────────────────────────
SARVAM_BASE = "https://api.sarvam.ai"

LANGUAGE_NAMES = {
    "hi-IN": "Hindi",
    "mr-IN": "Marathi",
    "ta-IN": "Tamil",
    "te-IN": "Telugu",
    "kn-IN": "Kannada",
    "gu-IN": "Gujarati",
    "bn-IN": "Bengali",
    "ml-IN": "Malayalam",
    "pa-IN": "Punjabi",
    "en-IN": "English",
}

DEFAULT_LANGUAGE_CODE = "mr-IN"
SUPPORTED_LANGUAGE_CODES = tuple(LANGUAGE_NAMES.keys())

LOCALIZED_FALLBACKS = {
    "en-IN": {
        "greeting": "Good morning, welcome to our bank. How can I help you today?",
        "repeat_service": "I could not hear that clearly. Please tell me again which banking service you need.",
        "repeat_brief": "I could not hear that clearly. Please briefly repeat which banking service you need.",
        "help_services": "I can help with account opening, fixed deposits, KYC, cards, loans, lockers, cheques, transfers, and other banking services. Please tell me what you need.",
        "form_yes_no": "Please say yes if you want me to start the form, or no if you want something else.",
        "no_problem": "No problem. Please tell me what else you would like help with.",
        "starting_form": "Great. I will start the {form_title} form now.",
        "form_retry": "I didn't catch that. {question}",
        "form_intro": "Welcome! I'll help you fill the {form_title} form. Let's start. {question}",
        "form_complete": "All fields are filled. Your {form_title} form is now complete. The staff can review and download the PDF.",
        "got_it_question": "Got it. {question}",
        "no_message": "No message is available.",
        "start_form_question": "Would you like me to start the form now?",
    },
    "mr-IN": {
        "greeting": "शुभ सकाळ, आमच्या बँकेत आपले स्वागत आहे. आज मी आपली कशी मदत करू शकतो?",
        "repeat_service": "मला नीट ऐकू आले नाही. कृपया पुन्हा सांगा, तुम्हाला कोणती बँक सेवा हवी आहे?",
        "repeat_brief": "मला नीट ऐकू आले नाही. कृपया थोडक्यात पुन्हा सांगा, तुम्हाला कोणती बँक सेवा हवी आहे?",
        "help_services": "मी खाते उघडणे, फिक्स्ड डिपॉझिट, KYC, कार्ड, कर्ज, लॉकर, चेक, ट्रान्सफर आणि इतर बँकिंग सेवांसाठी मदत करू शकतो. तुम्हाला काय हवे ते सांगा.",
        "form_yes_no": "फॉर्म सुरू करायचा असेल तर हो म्हणा, नाहीतर नाही म्हणा.",
        "no_problem": "काही हरकत नाही. आणखी कशासाठी मदत हवी ते सांगा.",
        "starting_form": "ठीक आहे. मी {form_title} फॉर्म सुरू करतो.",
        "form_retry": "मला नीट समजले नाही. {question}",
        "form_intro": "स्वागत आहे. मी {form_title} फॉर्म भरायला मदत करतो. चला सुरू करू. {question}",
        "form_complete": "सर्व माहिती भरली आहे. तुमचा {form_title} फॉर्म पूर्ण झाला आहे. कर्मचारी तपासून PDF डाउनलोड करू शकतात.",
        "got_it_question": "ठीक आहे. {question}",
        "no_message": "कोणताही संदेश उपलब्ध नाही.",
        "start_form_question": "मी फॉर्म सुरू करू का?",
    },
    "hi-IN": {
        "greeting": "सुप्रभात, हमारे बैंक में आपका स्वागत है। आज मैं आपकी कैसे मदद कर सकता हूँ?",
        "repeat_service": "मुझे ठीक से सुनाई नहीं दिया। कृपया फिर से बताइए कि आपको कौन सी बैंकिंग सेवा चाहिए।",
        "repeat_brief": "मुझे ठीक से सुनाई नहीं दिया। कृपया संक्षेप में फिर से बताइए कि आपको कौन सी सेवा चाहिए।",
        "help_services": "मैं खाता खोलने, फिक्स्ड डिपॉजिट, KYC, कार्ड, लोन, लॉकर, चेक, ट्रांसफर और अन्य बैंकिंग सेवाओं में मदद कर सकता हूँ। कृपया बताइए आपको क्या चाहिए।",
        "form_yes_no": "अगर आप फॉर्म शुरू करना चाहते हैं तो हाँ कहिए, नहीं तो ना कहिए।",
        "no_problem": "कोई बात नहीं। कृपया बताइए आपको और किस चीज़ में मदद चाहिए।",
        "starting_form": "ठीक है। मैं {form_title} फॉर्म शुरू कर रहा हूँ।",
        "form_retry": "मैं समझ नहीं पाया। {question}",
        "form_intro": "स्वागत है। मैं {form_title} फॉर्म भरने में मदद करूँगा। चलिए शुरू करते हैं। {question}",
        "form_complete": "सभी जानकारी भर दी गई है। आपका {form_title} फॉर्म पूरा हो गया है। स्टाफ इसे जाँचकर PDF डाउनलोड कर सकता है।",
        "got_it_question": "ठीक है। {question}",
        "no_message": "कोई संदेश उपलब्ध नहीं है।",
        "start_form_question": "क्या मैं फॉर्म शुरू करूँ?",
    },
    "gu-IN": {
        "greeting": "સુપ્રભાત, અમારી બેંકમાં આપનું સ્વાગત છે. આજે હું તમારી કેવી રીતે મદદ કરી શકું?",
        "repeat_service": "મને સ્પષ્ટ સાંભળાયું નથી. કૃપા કરીને ફરી કહો કે તમને કઈ બેંકિંગ સેવા જોઈએ છે.",
        "repeat_brief": "મને સ્પષ્ટ સાંભળાયું નથી. કૃપા કરીને ટૂંકમાં ફરી કહો કે તમને કઈ સેવા જોઈએ છે.",
        "help_services": "હું ખાતું ખોલવું, ફિક્સ્ડ ડિપોઝિટ, KYC, કાર્ડ, લોન, લોકર, ચેક, ટ્રાન્સફર અને અન્ય બેંકિંગ સેવાઓમાં મદદ કરી શકું છું. કૃપા કરીને તમારી જરૂર કહો.",
        "form_yes_no": "જો ફોર્મ શરૂ કરવું હોય તો હા કહો, નહીં તો ના કહો.",
        "no_problem": "કોઈ વાંધો નહીં. બીજી કઈ મદદ જોઈએ તે કહો.",
        "starting_form": "બરાબર. હું {form_title} ફોર્મ શરૂ કરું છું.",
        "form_retry": "હું સમજ્યો નથી. {question}",
        "form_intro": "સ્વાગત છે. હું {form_title} ફોર્મ ભરવામાં મદદ કરીશ. ચાલો શરૂ કરીએ. {question}",
        "form_complete": "બધી માહિતી ભરાઈ ગઈ છે. તમારું {form_title} ફોર્મ પૂર્ણ થયું છે. સ્ટાફ સમીક્ષા કરીને PDF ડાઉનલોડ કરી શકે છે.",
        "got_it_question": "બરાબર. {question}",
        "no_message": "કોઈ સંદેશ ઉપલબ્ધ નથી.",
        "start_form_question": "શું હું ફોર્મ શરૂ કરું?",
    },
    "kn-IN": {
        "greeting": "ಶುಭೋದಯ, ನಮ್ಮ ಬ್ಯಾಂಕಿಗೆ ಸ್ವಾಗತ. ಇಂದು ನಾನು ನಿಮಗೆ ಹೇಗೆ ಸಹಾಯ ಮಾಡಬಹುದು?",
        "repeat_service": "ನನಗೆ ಸ್ಪಷ್ಟವಾಗಿ ಕೇಳಿಸಲಿಲ್ಲ. ದಯವಿಟ್ಟು ನಿಮಗೆ ಯಾವ ಬ್ಯಾಂಕಿಂಗ್ ಸೇವೆ ಬೇಕು ಎಂದು ಮತ್ತೆ ಹೇಳಿ.",
        "repeat_brief": "ನನಗೆ ಸ್ಪಷ್ಟವಾಗಿ ಕೇಳಿಸಲಿಲ್ಲ. ದಯವಿಟ್ಟು ಸಂಕ್ಷಿಪ್ತವಾಗಿ ಮತ್ತೆ ಹೇಳಿ.",
        "help_services": "ಖಾತೆ ತೆರೆಯುವುದು, ಫಿಕ್ಸ್‌ಡ್ ಡೆಪಾಸಿಟ್, KYC, ಕಾರ್ಡ್, ಸಾಲ, ಲಾಕರ್, ಚೆಕ್, ವರ್ಗಾವಣೆ ಮತ್ತು ಇತರ ಬ್ಯಾಂಕಿಂಗ್ ಸೇವೆಗಳಲ್ಲಿ ನಾನು ಸಹಾಯ ಮಾಡಬಹುದು. ನಿಮಗೆ ಏನು ಬೇಕು ಹೇಳಿ.",
        "form_yes_no": "ಫಾರ್ಮ್ ಆರಂಭಿಸಬೇಕಾದರೆ ಹೌದು ಎಂದು ಹೇಳಿ, ಇಲ್ಲದಿದ್ದರೆ ಇಲ್ಲ ಎಂದು ಹೇಳಿ.",
        "no_problem": "ಸರಿ. ಇನ್ನೇನು ಸಹಾಯ ಬೇಕು ಹೇಳಿ.",
        "starting_form": "ಸರಿ. ನಾನು {form_title} ಫಾರ್ಮ್ ಆರಂಭಿಸುತ್ತೇನೆ.",
        "form_retry": "ನನಗೆ ಅರ್ಥವಾಗಲಿಲ್ಲ. {question}",
        "form_intro": "ಸ್ವಾಗತ. {form_title} ಫಾರ್ಮ್ ತುಂಬಲು ನಾನು ಸಹಾಯ ಮಾಡುತ್ತೇನೆ. ಶುರು ಮಾಡೋಣ. {question}",
        "form_complete": "ಎಲ್ಲಾ ಮಾಹಿತಿಯನ್ನು ತುಂಬಲಾಗಿದೆ. ನಿಮ್ಮ {form_title} ಫಾರ್ಮ್ ಪೂರ್ಣವಾಗಿದೆ. ಸಿಬ್ಬಂದಿ ಪರಿಶೀಲಿಸಿ PDF ಡೌನ್‌ಲೋಡ್ ಮಾಡಬಹುದು.",
        "got_it_question": "ಸರಿ. {question}",
        "no_message": "ಯಾವುದೇ ಸಂದೇಶ ಲಭ್ಯವಿಲ್ಲ.",
        "start_form_question": "ನಾನು ಫಾರ್ಮ್ ಆರಂಭಿಸಬೇಕೆ?",
    },
    "ta-IN": {
        "greeting": "காலை வணக்கம், எங்கள் வங்கிக்கு வரவேற்கிறோம். இன்று நான் எப்படி உதவலாம்?",
        "repeat_service": "தெளிவாக கேட்கவில்லை. உங்களுக்கு எந்த வங்கி சேவை வேண்டும் என்பதை மீண்டும் சொல்லுங்கள்.",
        "repeat_brief": "தெளிவாக கேட்கவில்லை. தயவுசெய்து சுருக்கமாக மீண்டும் சொல்லுங்கள்.",
        "help_services": "கணக்கு திறப்பு, நிரந்தர வைப்பு, KYC, கார்டுகள், கடன்கள், லாக்கர், காசோலை, பரிமாற்றம் மற்றும் பிற வங்கி சேவைகளில் உதவ முடியும். உங்களுக்கு என்ன வேண்டும் என்று சொல்லுங்கள்.",
        "form_yes_no": "படிவத்தை தொடங்க விரும்பினால் ஆம் சொல்லுங்கள், இல்லையெனில் இல்லை சொல்லுங்கள்.",
        "no_problem": "பரவாயில்லை. வேறு எந்த உதவி வேண்டும் என்று சொல்லுங்கள்.",
        "starting_form": "சரி. நான் {form_title} படிவத்தை தொடங்குகிறேன்.",
        "form_retry": "எனக்கு புரியவில்லை. {question}",
        "form_intro": "வரவேற்கிறோம். {form_title} படிவத்தை நிரப்ப உதவுகிறேன். தொடங்கலாம். {question}",
        "form_complete": "அனைத்து விவரங்களும் நிரப்பப்பட்டுள்ளன. உங்கள் {form_title} படிவம் முடிந்தது. பணியாளர் சரிபார்த்து PDF பதிவிறக்கலாம்.",
        "got_it_question": "சரி. {question}",
        "no_message": "செய்தி எதுவும் இல்லை.",
        "start_form_question": "நான் படிவத்தை தொடங்கலாமா?",
    },
    "te-IN": {
        "greeting": "శుభోదయం, మా బ్యాంకుకు స్వాగతం. ఈ రోజు నేను మీకు ఎలా సహాయం చేయగలను?",
        "repeat_service": "స్పష్టంగా వినిపించలేదు. దయచేసి మీకు ఏ బ్యాంకింగ్ సేవ కావాలో మళ్లీ చెప్పండి.",
        "repeat_brief": "స్పష్టంగా వినిపించలేదు. దయచేసి సంక్షిప్తంగా మళ్లీ చెప్పండి.",
        "help_services": "ఖాతా ప్రారంభం, ఫిక్స్డ్ డిపాజిట్, KYC, కార్డులు, రుణాలు, లాకర్, చెక్కులు, బదిలీలు మరియు ఇతర బ్యాంకింగ్ సేవల్లో నేను సహాయం చేయగలను. మీకు ఏమి కావాలో చెప్పండి.",
        "form_yes_no": "ఫారమ్ ప్రారంభించాలంటే అవును చెప్పండి, లేదంటే కాదు చెప్పండి.",
        "no_problem": "పరవాలేదు. ఇంకేం సహాయం కావాలో చెప్పండి.",
        "starting_form": "సరే. నేను {form_title} ఫారమ్ ప్రారంభిస్తున్నాను.",
        "form_retry": "నాకు అర్థం కాలేదు. {question}",
        "form_intro": "స్వాగతం. {form_title} ఫారమ్ నింపడంలో సహాయం చేస్తాను. ప్రారంభిద్దాం. {question}",
        "form_complete": "అన్ని వివరాలు నింపబడ్డాయి. మీ {form_title} ఫారమ్ పూర్తయింది. సిబ్బంది పరిశీలించి PDF డౌన్‌లోడ్ చేయవచ్చు.",
        "got_it_question": "సరే. {question}",
        "no_message": "సందేశం అందుబాటులో లేదు.",
        "start_form_question": "నేను ఫారమ్ ప్రారంభించాలా?",
    },
    "bn-IN": {
        "greeting": "সুপ্রভাত, আমাদের ব্যাংকে আপনাকে স্বাগতম। আজ আমি কীভাবে সাহায্য করতে পারি?",
        "repeat_service": "আমি পরিষ্কার শুনতে পাইনি। অনুগ্রহ করে আবার বলুন আপনার কোন ব্যাংকিং পরিষেবা দরকার।",
        "repeat_brief": "আমি পরিষ্কার শুনতে পাইনি। অনুগ্রহ করে সংক্ষেপে আবার বলুন।",
        "help_services": "আমি অ্যাকাউন্ট খোলা, ফিক্সড ডিপোজিট, KYC, কার্ড, ঋণ, লকার, চেক, ট্রান্সফার এবং অন্যান্য ব্যাংকিং পরিষেবায় সাহায্য করতে পারি। কী দরকার বলুন।",
        "form_yes_no": "ফর্ম শুরু করতে চাইলে হ্যাঁ বলুন, না হলে না বলুন।",
        "no_problem": "কোনো সমস্যা নেই। আর কী সাহায্য দরকার বলুন।",
        "starting_form": "ঠিক আছে। আমি {form_title} ফর্ম শুরু করছি।",
        "form_retry": "আমি বুঝতে পারিনি। {question}",
        "form_intro": "স্বাগতম। আমি {form_title} ফর্ম পূরণে সাহায্য করব। শুরু করি। {question}",
        "form_complete": "সব তথ্য পূরণ হয়েছে। আপনার {form_title} ফর্ম সম্পূর্ণ। স্টাফ দেখে PDF ডাউনলোড করতে পারবেন।",
        "got_it_question": "ঠিক আছে। {question}",
        "no_message": "কোনো বার্তা উপলব্ধ নেই।",
        "start_form_question": "আমি কি ফর্ম শুরু করব?",
    },
    "ml-IN": {
        "greeting": "സുപ്രഭാതം, ഞങ്ങളുടെ ബാങ്കിലേക്ക് സ്വാഗതം. ഇന്ന് എങ്ങനെ സഹായിക്കാം?",
        "repeat_service": "വ്യക്തമായി കേൾക്കാനായില്ല. നിങ്ങൾക്ക് ഏത് ബാങ്കിംഗ് സേവനമാണ് വേണ്ടത് എന്ന് വീണ്ടും പറയൂ.",
        "repeat_brief": "വ്യക്തമായി കേൾക്കാനായില്ല. ദയവായി ചുരുക്കത്തിൽ വീണ്ടും പറയൂ.",
        "help_services": "അക്കൗണ്ട് തുറക്കൽ, ഫിക്സഡ് ഡെപ്പോസിറ്റ്, KYC, കാർഡുകൾ, വായ്പകൾ, ലോക്കർ, ചെക്കുകൾ, ട്രാൻസ്ഫറുകൾ, മറ്റ് ബാങ്കിംഗ് സേവനങ്ങൾ എന്നിവയിൽ ഞാൻ സഹായിക്കാം. എന്താണ് വേണ്ടത് പറയൂ.",
        "form_yes_no": "ഫോം തുടങ്ങണമെങ്കിൽ അതെ എന്ന് പറയൂ, അല്ലെങ്കിൽ ഇല്ല എന്ന് പറയൂ.",
        "no_problem": "പ്രശ്നമില്ല. മറ്റെന്ത് സഹായം വേണമെന്ന് പറയൂ.",
        "starting_form": "ശരി. ഞാൻ {form_title} ഫോം തുടങ്ങുന്നു.",
        "form_retry": "എനിക്ക് മനസ്സിലായില്ല. {question}",
        "form_intro": "സ്വാഗതം. {form_title} ഫോം പൂരിപ്പിക്കാൻ ഞാൻ സഹായിക്കും. തുടങ്ങാം. {question}",
        "form_complete": "എല്ലാ വിവരങ്ങളും പൂരിപ്പിച്ചു. നിങ്ങളുടെ {form_title} ഫോം പൂർത്തിയായി. സ്റ്റാഫിന് പരിശോധിച്ച് PDF ഡൗൺലോഡ് ചെയ്യാം.",
        "got_it_question": "ശരി. {question}",
        "no_message": "സന്ദേശം ലഭ്യമല്ല.",
        "start_form_question": "ഞാൻ ഫോം തുടങ്ങട്ടേ?",
    },
    "pa-IN": {
        "greeting": "ਸ਼ੁਭ ਸਵੇਰ, ਸਾਡੇ ਬੈਂਕ ਵਿੱਚ ਤੁਹਾਡਾ ਸਵਾਗਤ ਹੈ। ਅੱਜ ਮੈਂ ਤੁਹਾਡੀ ਕਿਵੇਂ ਮਦਦ ਕਰ ਸਕਦਾ ਹਾਂ?",
        "repeat_service": "ਮੈਨੂੰ ਸਾਫ਼ ਸੁਣਾਈ ਨਹੀਂ ਦਿੱਤਾ। ਕਿਰਪਾ ਕਰਕੇ ਫਿਰ ਦੱਸੋ ਤੁਹਾਨੂੰ ਕਿਹੜੀ ਬੈਂਕਿੰਗ ਸੇਵਾ ਚਾਹੀਦੀ ਹੈ।",
        "repeat_brief": "ਮੈਨੂੰ ਸਾਫ਼ ਸੁਣਾਈ ਨਹੀਂ ਦਿੱਤਾ। ਕਿਰਪਾ ਕਰਕੇ ਸੰਖੇਪ ਵਿੱਚ ਫਿਰ ਦੱਸੋ।",
        "help_services": "ਮੈਂ ਖਾਤਾ ਖੋਲ੍ਹਣ, ਫਿਕਸਡ ਡਿਪਾਜ਼ਿਟ, KYC, ਕਾਰਡ, ਕਰਜ਼ੇ, ਲਾਕਰ, ਚੈੱਕ, ਟ੍ਰਾਂਸਫਰ ਅਤੇ ਹੋਰ ਬੈਂਕਿੰਗ ਸੇਵਾਵਾਂ ਵਿੱਚ ਮਦਦ ਕਰ ਸਕਦਾ ਹਾਂ। ਦੱਸੋ ਤੁਹਾਨੂੰ ਕੀ ਚਾਹੀਦਾ ਹੈ।",
        "form_yes_no": "ਜੇ ਤੁਸੀਂ ਫਾਰਮ ਸ਼ੁਰੂ ਕਰਨਾ ਚਾਹੁੰਦੇ ਹੋ ਤਾਂ ਹਾਂ ਕਹੋ, ਨਹੀਂ ਤਾਂ ਨਹੀਂ ਕਹੋ।",
        "no_problem": "ਕੋਈ ਗੱਲ ਨਹੀਂ। ਹੋਰ ਕਿਸ ਮਦਦ ਦੀ ਲੋੜ ਹੈ ਦੱਸੋ।",
        "starting_form": "ਠੀਕ ਹੈ। ਮੈਂ {form_title} ਫਾਰਮ ਸ਼ੁਰੂ ਕਰਦਾ ਹਾਂ।",
        "form_retry": "ਮੈਨੂੰ ਸਮਝ ਨਹੀਂ ਆਇਆ। {question}",
        "form_intro": "ਸਵਾਗਤ ਹੈ। ਮੈਂ {form_title} ਫਾਰਮ ਭਰਨ ਵਿੱਚ ਮਦਦ ਕਰਾਂਗਾ। ਆਓ ਸ਼ੁਰੂ ਕਰੀਏ। {question}",
        "form_complete": "ਸਾਰੀ ਜਾਣਕਾਰੀ ਭਰ ਦਿੱਤੀ ਗਈ ਹੈ। ਤੁਹਾਡਾ {form_title} ਫਾਰਮ ਪੂਰਾ ਹੋ ਗਿਆ ਹੈ। ਸਟਾਫ਼ ਜਾਂਚ ਕੇ PDF ਡਾਊਨਲੋਡ ਕਰ ਸਕਦਾ ਹੈ।",
        "got_it_question": "ਠੀਕ ਹੈ। {question}",
        "no_message": "ਕੋਈ ਸੁਨੇਹਾ ਉਪਲਬਧ ਨਹੀਂ ਹੈ।",
        "start_form_question": "ਕੀ ਮੈਂ ਫਾਰਮ ਸ਼ੁਰੂ ਕਰਾਂ?",
    },
}

FORM_INTENT_KEYWORDS = {
    "fd_application": ["open fd", "start fd", "apply fd", "fd form", "fixed deposit open", "fixed deposit apply", "fd application", "एफडी उघड", "एफडी करायचा", "fd करायचा"],
    "account_opening": [
        "open account", "new account", "account open", "open a bank", "start account",
        "account application", "खाते उघड", "खाते काढ", "अकाउंट उघड", "खाते उघडायचे",
    ],
    "loan_application": ["apply loan", "loan apply", "loan application", "loan form", "लोन अर्ज", "कर्ज अर्ज"],
    "kyc": ["kyc update", "kyc form", "update kyc", "kyc verification", "केवायसी अपडेट"],
    "card_application": ["apply card", "card application", "new card apply", "card form", "कार्ड अर्ज"],
}

FORM_TITLES = {
    "fd_application": "Fixed Deposit Application",
    "account_opening": "Account Opening",
    "loan_application": "Loan Application",
    "kyc": "KYC Verification",
    "card_application": "Card Application",
}

FORM_TITLES_MR = {
    "Fixed Deposit Application": "फिक्स्ड डिपॉझिट अर्ज",
    "Account Opening": "खाते उघडण्याचा अर्ज",
    "Loan Application": "कर्ज अर्ज",
    "KYC Verification": "KYC पडताळणी",
    "Card Application": "कार्ड अर्ज",
}

FORM_QUESTIONS_MR = {
    "What is your full name as it appears on your ID?": "तुमच्या ओळखपत्रावर जसे नाव आहे तसे तुमचे पूर्ण नाव काय आहे?",
    "What is your full name?": "तुमचे पूर्ण नाव काय आहे?",
    "What is your date of birth?": "तुमची जन्मतारीख काय आहे?",
    "What is your PAN card number?": "तुमचा PAN कार्ड नंबर काय आहे?",
    "Please tell me your PAN number.": "कृपया तुमचा PAN नंबर सांगा.",
    "What is your PAN number?": "तुमचा PAN नंबर काय आहे?",
    "What is your Aadhaar number?": "तुमचा Aadhaar नंबर काय आहे?",
    "What is your current residential address?": "तुमचा सध्याचा निवासी पत्ता काय आहे?",
    "What is your residential address?": "तुमचा निवासी पत्ता काय आहे?",
    "Which city do you live in?": "तुम्ही कोणत्या शहरात राहता?",
    "Which state?": "तुमचे राज्य कोणते आहे?",
    "What is your area PIN code?": "तुमच्या भागाचा PIN code काय आहे?",
    "What is your mobile phone number?": "तुमचा mobile phone number काय आहे?",
    "What is your mobile number?": "तुमचा mobile number काय आहे?",
    "What is your email address?": "तुमचा email address काय आहे?",
    "What is your occupation?": "तुमचा व्यवसाय काय आहे?",
    "What is your approximate annual income?": "तुमचे अंदाजे वार्षिक उत्पन्न किती आहे?",
    "What type of account would you like to open — Savings or Current?": "तुम्हाला कोणते खाते उघडायचे आहे, Savings की Current?",
    "Who would you like to nominate for this account?": "या खात्यासाठी nominee म्हणून कोणाचे नाव द्यायचे आहे?",
    "What is your relationship with the nominee?": "nominee सोबत तुमचे नाते काय आहे?",
    "How much would you like to deposit as the opening amount?": "खाते सुरू करताना तुम्हाला किती रक्कम जमा करायची आहे?",
    "What is your existing bank account number for this FD?": "या FD साठी तुमचा विद्यमान bank account number काय आहे?",
    "How much would you like to invest in the fixed deposit?": "फिक्स्ड डिपॉझिटमध्ये तुम्हाला किती रक्कम गुंतवायची आहे?",
    "For how many months would you like the fixed deposit?": "तुम्हाला किती महिन्यांसाठी fixed deposit करायची आहे?",
    "Would you like monthly interest payout or reinvestment at maturity?": "तुम्हाला monthly interest payout पाहिजे की maturity वेळी reinvestment पाहिजे?",
    "Who is the nominee for this fixed deposit?": "या fixed deposit साठी nominee कोण आहे?",
    "What type of loan are you looking for — Personal, Home, or Vehicle?": "तुम्हाला कोणत्या प्रकारचे loan हवे आहे, Personal, Home की Vehicle?",
    "How much loan amount do you need?": "तुम्हाला किती loan amount हवी आहे?",
    "What is the purpose of this loan?": "या loan चा उद्देश काय आहे?",
    "Are you salaried, self-employed, or a business owner?": "तुम्ही salaried, self-employed की business owner आहात?",
    "What is your monthly income?": "तुमचे monthly income किती आहे?",
    "Do you have any existing loan EMIs? If yes, what is the total monthly EMI amount?": "तुमच्याकडे आधीपासून काही loan EMI आहेत का? असल्यास एकूण monthly EMI किती आहे?",
    "What is your full name as you want it printed on the card?": "कार्डवर जसे नाव छापायचे आहे तसे तुमचे पूर्ण नाव काय आहे?",
    "What is your registered mobile number?": "तुमचा registered mobile number काय आहे?",
    "Would you like a Debit card or a Credit card?": "तुम्हाला Debit card पाहिजे की Credit card?",
    "What credit limit would you prefer? You can say a range.": "तुम्हाला कोणती credit limit हवी आहे? तुम्ही अंदाजे range सांगू शकता.",
    "What address should be used for billing?": "billing साठी कोणता पत्ता वापरायचा आहे?",
    "Where should we deliver the card? Same as billing address or a different one?": "कार्ड कुठे deliver करायचे? Billing address सारखाच की वेगळा पत्ता?",
}

AFFIRMATIVE_TERMS = {
    "yes", "yeah", "yep", "sure", "ok", "okay", "start", "proceed", "continue",
    "करा", "हो", "होय", "चालू", "शुरू", "हाँ", "हा", "ji", "haan",
}

NEGATIVE_TERMS = {
    "no", "nope", "not now", "later", "cancel", "stop", "don't", "dont", "do not",
    "not interested", "i don't want", "i do not want", "नको", "नकोय", "नाही", "मत", "रद्द",
}

INFO_REQUEST_TERMS = {
    "document", "documents", "doc", "docs", "required", "requirement", "requirements",
    "need", "needed", "bring", "interest", "rate", "rates", "charges", "fee", "fees",
    "eligibility", "explain", "tell", "information", "info", "what", "how",
    "कागदपत्र", "कागदपत्रे", "डॉक्युमेंट", "डॉक्युमेंट्स", "लाग", "लागतील", "हवे",
    "काय", "कसा", "कशी", "माहिती", "व्याज", "दर", "चार्ज", "फी",
}

NEGATIVE_SENTIMENT_TERMS = {
    "angry", "upset", "frustrated", "bad", "worst", "complaint", "complain", "problem", "issue",
    "delay", "waiting", "नाराज", "राग", "तक्रार", "समस्या", "प्रॉब्लेम", "परेशान", "गुस्सा",
}

POSITIVE_SENTIMENT_TERMS = {"thanks", "thank you", "good", "great", "helpful", "धन्यवाद", "छान", "ठीक"}

PRODUCT_EXPLAINERS = {
    "fd_application": (
        "A fixed deposit lets you place a lump sum for a chosen tenure and earn a fixed rate. "
        "From the configured branch rate table, regular FD rates are typically 3.50% to 7.10% per annum, "
        "and senior citizens may get an additional 0.50%, subject to bank policy and tenure. "
        "You will usually need an existing savings account, PAN, Aadhaar or valid KYC, deposit amount, tenure, "
        "interest payout choice, and nominee details. Interest can be paid monthly, quarterly, or reinvested at maturity. "
        "Premature withdrawal may reduce the applicable rate and may attract a penalty, and TDS can apply as per tax rules. "
        "Would you like me to start the Fixed Deposit Application form now?"
    ),
    "account_opening": (
        "To open a bank account, you usually need PAN card, Aadhaar or another valid identity and address proof, "
        "mobile number, email if available, one passport-size photo if the branch requires it, nominee details, "
        "and the initial deposit amount if that account type has a minimum opening balance. "
        "The staff will verify KYC and explain charges or minimum balance rules before submission. "
        "Would you like me to start the Account Opening form now?"
    ),
    "loan_application": (
        "For a loan enquiry, we first collect income, employment type, loan amount, purpose, and existing EMI details. "
        "Interest rate, processing fee, and approval depend on credit assessment, so approval must not be promised. "
        "Would you like me to start the Loan Application form now?"
    ),
    "kyc": (
        "For KYC verification or update, we collect identity, address, PAN, Aadhaar, phone, and supporting details. "
        "The staff must verify documents and complete required authentication. Would you like me to start the KYC form now?"
    ),
    "card_application": (
        "For a debit or credit card request, we collect name, PAN, registered mobile number, card type, billing address, "
        "delivery address, and any credit limit preference for credit cards. Would you like me to start the Card Application form now?"
    ),
}

PRODUCT_EXPLAINERS_MR = {
    "fd_application": (
        "फिक्स्ड डिपॉझिटमध्ये तुम्ही ठराविक रक्कम ठराविक कालावधीसाठी ठेवता आणि निश्चित व्याज मिळते. "
        "या डेमोमधील शाखा दरांनुसार सामान्य FD दर साधारण 3.50% ते 7.10% वार्षिक असू शकतात, "
        "आणि ज्येष्ठ नागरिकांना धोरणानुसार अतिरिक्त 0.50% मिळू शकते. FD साठी साधारणपणे बचत खाते, PAN, Aadhaar किंवा वैध KYC, "
        "ठेव रक्कम, कालावधी, व्याज कसे घ्यायचे आणि nominee तपशील लागतात. Premature withdrawal केल्यास दर कमी होऊ शकतो, penalty लागू होऊ शकते, "
        "आणि कर नियमानुसार TDS लागू होऊ शकतो. आपण FD application form भरायला सुरुवात करू का?"
    ),
    "account_opening": (
        "बँक खाते उघडण्यासाठी साधारणपणे PAN card, Aadhaar किंवा इतर वैध ओळख आणि पत्त्याचा पुरावा, mobile number, email असल्यास email, "
        "शाखेला गरज असल्यास एक passport-size photo, nominee details आणि account type नुसार initial deposit amount लागते. "
        "Staff KYC verify करेल आणि minimum balance किंवा charges आधी समजावून सांगेल. आपण Account Opening form भरायला सुरुवात करू का?"
    ),
    "loan_application": (
        "Loan साठी आम्ही income, employment type, loan amount, purpose आणि existing EMI details घेतो. "
        "Interest rate, processing fee आणि approval credit assessment वर अवलंबून असते, म्हणून approval guarantee देता येत नाही. "
        "आपण Loan Application form भरायला सुरुवात करू का?"
    ),
    "kyc": (
        "KYC verification किंवा update साठी ओळख पुरावा, address proof, PAN, Aadhaar, phone number आणि supporting details लागतात. "
        "Staff documents verify करून required authentication पूर्ण करेल. आपण KYC form भरायला सुरुवात करू का?"
    ),
    "card_application": (
        "Debit किंवा Credit card request साठी card वर छापायचे नाव, PAN, registered mobile number, card type, billing address, delivery address "
        "आणि credit card असल्यास preferred credit limit लागते. आपण Card Application form भरायला सुरुवात करू का?"
    ),
}

NON_FORM_TOPIC_KEYWORDS = {
    "cheque_services": [
        "cheque", "check bounce", "bounce check", "bounced check", "cheque bounce", "bounced cheque",
        "cheque return", "returned cheque", "stop cheque", "stop payment", "cts",
        "चेक", "धनादेश", "बाउन्स", "बाउंस", "परत", "रिटर्न", "वटला नाही",
    ],
    "fund_transfer": ["neft", "rtgs", "imps", "transfer", "remittance", "ट्रान्सफर", "हस्तांतरण"],
    "locker_services": ["locker", "safe deposit", "लॉकर"],
    "rd_services": ["recurring deposit", "rd", "आरडी"],
    "ppf_services": ["ppf", "public provident", "पीपीएफ"],
    "insurance": ["insurance", "ulip", "policy", "इन्शुरन्स", "विमा"],
}

# ── Marathi keyword → English RAG query hint map ─────────────────────────────
# Used as a last-resort fallback when Sarvam translation returns the source text
# unchanged.  Keys are lowercase Marathi substrings; values are plain English
# query strings that will match your English KB chunks correctly.
MARATHI_QUERY_HINT_MAP: list[tuple[str, str]] = [
    # Account opening
    ("खाते उघड",     "how to open a bank account documents required"),
    ("खाते काढ",     "how to open a bank account documents required"),
    ("अकाउंट उघड",  "how to open a bank account documents required"),
    ("खाते उघडाय",   "how to open a bank account documents required"),
    ("नवीन खाते",    "new bank account opening requirements"),
    ("बचत खाते",     "savings account opening documents"),
    ("बचत खाता",     "savings account opening documents"),
    ("चालू खाते",    "current account opening documents"),
    # Fixed deposit
    ("एफडी",         "fixed deposit interest rate documents"),
    ("fd करायच",     "how to start a fixed deposit"),
    ("मुदत ठेव",     "fixed deposit interest rate tenure"),
    ("फिक्स्ड डिपॉ", "fixed deposit interest rate charges"),
    # Loan
    ("कर्ज",         "loan eligibility documents interest rate"),
    ("लोन",          "loan application documents eligibility"),
    ("गृहकर्ज",      "home loan eligibility documents"),
    ("वाहन कर्ज",    "vehicle loan documents interest"),
    ("वैयक्तिक कर्ज","personal loan eligibility documents"),
    # KYC
    ("केवायसी",      "KYC verification documents required"),
    ("kyc अपडेट",    "KYC update documents required"),
    # Card
    ("कार्ड",        "debit credit card application documents"),
    ("डेबिट कार्ड", "debit card application process"),
    ("क्रेडिट कार्ड","credit card application eligibility limit"),
    # Cheque
    ("चेक",          "cheque bounce charges return rules"),
    ("धनादेश",       "cheque services bounce return"),
    ("बाउन्स",       "cheque bounce charges penalty"),
    ("बाउंस",        "cheque bounce charges penalty"),
    ("वटला नाही",    "cheque return insufficient funds charges"),
    ("स्टॉप पेमेंट", "stop cheque payment charges process"),
    # Fund transfer
    ("ट्रान्सफर",    "NEFT RTGS IMPS fund transfer charges"),
    ("हस्तांतरण",    "fund transfer NEFT RTGS process"),
    # Locker
    ("लॉकर",         "safe deposit locker charges eligibility"),
    # RD
    ("आरडी",         "recurring deposit interest rate tenure"),
    ("आवर्ती ठेव",   "recurring deposit RD documents"),
    # PPF
    ("पीपीएफ",       "PPF public provident fund interest rules"),
    # Insurance
    ("विमा",         "insurance policy banking"),
    ("इन्शुरन्स",   "insurance policy banking"),
    # Generic info
    ("कागदपत्र",     "documents required banking service"),
    ("डॉक्युमेंट",   "documents required banking service"),
    ("व्याज दर",     "interest rate banking products"),
    ("शुल्क",        "service charges fees banking"),
    ("माहिती",       "banking service information"),
    ("नियम",         "banking rules policy"),
    ("पात्रता",      "eligibility criteria banking"),
    # Net banking / ATM
    ("नेट बँकिंग",   "net banking internet banking registration"),
    ("एटीएम",        "ATM card services pin"),
    # Nomination
    ("नॉमिनी",       "nominee nomination banking account"),
    ("नामांकन",      "nominee nomination banking account"),
]


def _truncate_for_tts(text: str, max_chars: int = 500) -> str:
    """Truncate text at sentence boundary for natural TTS playback."""
    if not text or len(text) <= max_chars:
        return text
    # Try to cut at sentence boundary (. । ! ?)
    truncated = text[:max_chars]
    # Find last sentence end
    for sep in ['. ', '। ', '? ', '! ', '\n']:
        last_pos = truncated.rfind(sep)
        if last_pos > max_chars * 0.4:  # At least 40% of text
            return truncated[:last_pos + 1].strip()
    # Fallback: cut at last space
    last_space = truncated.rfind(' ')
    if last_space > max_chars * 0.4:
        return truncated[:last_space].strip()
    return truncated.strip()


class AIOrchestrator:
    """Provider boundary for STT, translation, entity extraction, RAG, and guardrails."""

    def __init__(self) -> None:
        self._http: httpx.AsyncClient | None = None
        self.detected_language: str | None = None
        self.detected_language_code: str | None = None
        self.last_translated_text: str = ""
        self.last_language_code: str = DEFAULT_LANGUAGE_CODE
        self.branch_id: str = settings.default_branch_id
        self.negative_streak: int = 0
        self.transcript_history: list[dict] = []
        # Form interview state
        self.form_session: FormSession | None = None
        self.pending_form_type: str | None = None
        self.awaiting_form_confirmation: bool = False

    @property
    def http(self) -> httpx.AsyncClient:
        if self._http is None or self._http.is_closed:
            self._http = httpx.AsyncClient(timeout=30)
        return self._http

    async def close(self) -> None:
        """Release per-session network resources."""
        if self._http is not None and not self._http.is_closed:
            await self._http.aclose()

    @property
    def sarvam_headers(self) -> dict:
        """Headers for JSON-bodied Sarvam endpoints (TTS, Chat)."""
        return {
            "api-subscription-key": settings.sarvam_api_key or "",
            "Content-Type": "application/json",
        }

    @property
    def sarvam_auth_headers(self) -> dict:
        """Headers for multipart Sarvam endpoints (e.g. STT). No Content-Type — httpx sets it."""
        return {"api-subscription-key": settings.sarvam_api_key or ""}

    # ── Sarvam: Speech-to-Text ───────────────────────────────────────────────
    async def _call_sarvam_stt(self, audio_bytes: bytes, language_code: str | None = None) -> dict:
        """POST audio to Sarvam saaras:v3 STT via multipart form-data.

        Returns {transcript, language_code, confidence}.
        """
        if not settings.sarvam_api_key:
            return {
                "transcript": None,
                "language_code": self._supported_language_code(language_code),
                "confidence": 0.0,
            }

        try:
            files = {"file": ("audio.wav", audio_bytes, "audio/wav")}
            # "unknown" is Sarvam saaras:v3's auto-detect sentinel.  Any other
            # value is validated via _supported_language_code first.
            if language_code == "unknown":
                lang_code = "unknown"
            else:
                lang_code = self._supported_language_code(language_code or self.detected_language_code)
            data = {
                "model": "saaras:v3",
                "language_code": lang_code,
                "mode": "transcribe",
            }
            logger.info("Calling Sarvam STT with lang_code: %s", lang_code)
            resp = await self.http.post(
                f"{SARVAM_BASE}/speech-to-text",
                files=files,
                data=data,
                headers=self.sarvam_auth_headers,
            )
            if resp.status_code != 200:
                logger.error("Sarvam STT error response: %s", resp.text)
            resp.raise_for_status()
            result = resp.json()
            transcript = result.get("transcript", "")
            lang_code = self._supported_language_code(result.get("language_code", lang_code))
            confidence = self._extract_stt_confidence(result)
            if transcript and confidence == 0.0:
                # Sarvam often omits confidence for otherwise valid transcripts.
                # Treat present text as usable instead of showing a false 0% warning.
                confidence = 0.86
            logger.info(
                "Sarvam STT result: lang=%s, confidence=%.2f, text=%s",
                lang_code,
                confidence,
                transcript[:80] if transcript else "(empty)",
            )
            return {"transcript": transcript or None, "language_code": lang_code, "confidence": confidence}
        except Exception as e:
            logger.error("Sarvam STT failed: %s", e)
            return {"transcript": None, "language_code": self._supported_language_code(language_code), "confidence": 0.0}

    def _normalize_confidence(self, value: object) -> float | None:
        try:
            score = float(value)
        except (TypeError, ValueError):
            return None
        if score > 1:
            score = score / 100
        return max(0.0, min(1.0, score))

    def _extract_stt_confidence(self, result: dict) -> float:
        for key in ("confidence", "confidence_score", "transcript_confidence", "asr_confidence"):
            score = self._normalize_confidence(result.get(key))
            if score is not None:
                return score

        scores: list[float] = []
        for list_key in ("words", "word_timestamps", "tokens", "segments"):
            for item in result.get(list_key, []) or []:
                if not isinstance(item, dict):
                    continue
                for key in ("confidence", "confidence_score", "score"):
                    score = self._normalize_confidence(item.get(key))
                    if score is not None:
                        scores.append(score)
                        break

        if scores:
            return sum(scores) / len(scores)
        return 0.0

    def _language_info_from_code(self, lang_code: str | None) -> dict:
        code = self._supported_language_code(lang_code)
        return {"language": LANGUAGE_NAMES.get(code, "English"), "code": code}

    def _supported_language_code(self, lang_code: str | None) -> str:
        code = lang_code or self.detected_language_code or DEFAULT_LANGUAGE_CODE
        return code if code in LANGUAGE_NAMES else "en-IN"

    def _fallback_text(self, key: str, lang_code: str | None = None, **kwargs: str) -> str:
        code = self._supported_language_code(lang_code)
        text = LOCALIZED_FALLBACKS.get(code, LOCALIZED_FALLBACKS["en-IN"]).get(
            key,
            LOCALIZED_FALLBACKS["en-IN"][key],
        )
        return text.format(**kwargs)

    async def _localized_phrase(self, key: str, lang_code: str | None = None, **kwargs: str) -> str:
        code = self._supported_language_code(lang_code)
        english = LOCALIZED_FALLBACKS["en-IN"][key].format(**kwargs)
        fallback = self._fallback_text(key, code, **kwargs)
        if code == "en-IN" or fallback != english:
            return fallback
        translated = await self._call_sarvam_translate(english, "en-IN", code)
        return translated if translated and translated != english else fallback

    async def _localized_form_title(self, title: str, lang_code: str | None = None) -> str:
        code = self._supported_language_code(lang_code)
        if code == "mr-IN":
            return FORM_TITLES_MR.get(title, title)
        if code != "en-IN":
            translated = await self._call_sarvam_translate(title, "en-IN", code)
            return translated if translated and translated != title else title
        return title

    async def _localized_form_question(self, question: str, lang_code: str | None = None) -> str:
        code = self._supported_language_code(lang_code)
        if code == "mr-IN":
            return FORM_QUESTIONS_MR.get(question, question)
        if code != "en-IN":
            translated = await self._call_sarvam_translate(question, "en-IN", code)
            return translated if translated and translated != question else question
        return question

    def set_language(self, lang_code: str) -> dict:
        lang_info = self._language_info_from_code(lang_code)
        self.detected_language = lang_info["language"]
        self.detected_language_code = lang_info["code"]
        self.last_language_code = lang_info["code"]
        return lang_info

    def set_branch(self, branch_id: str | None) -> None:
        self.branch_id = branch_id or settings.default_branch_id

    # ── Sarvam: Text-to-Speech ───────────────────────────────────────────────
    async def _call_sarvam_tts(self, text: str, language_code: str) -> str | None:
        """POST to Sarvam bulbul:v2 TTS. Returns base64 audio string."""
        if not settings.sarvam_api_key:
            return None

        # Truncate to ~500 chars at a sentence boundary for natural speech
        tts_text = _truncate_for_tts(text, max_chars=500)

        try:
            resp = await self.http.post(
                f"{SARVAM_BASE}/text-to-speech",
                json={
                    "inputs": [tts_text],
                    "target_language_code": language_code,
                    "speaker": "anushka",
                    "model": "bulbul:v2",
                },
                headers=self.sarvam_headers,
            )
            resp.raise_for_status()
            data = resp.json()
            # TTS returns {"audios": ["base64..."]}
            audios = data.get("audios", [])
            return audios[0] if audios else None
        except Exception as e:
            logger.error("Sarvam TTS failed: %s", e)
            return None

    async def build_assistant_message(self, text: str, language_code: str | None = None) -> dict:
        """Create a broadcastable assistant message with optional TTS audio."""
        lang_code = self._supported_language_code(language_code)
        lang_name = LANGUAGE_NAMES.get(lang_code, "English")
        audio_b64 = None if settings.ai_async_tts else await self._call_sarvam_tts(text, lang_code)
        now = datetime.now().strftime("%H:%M")
        item = TranscriptItem(
            id=str(uuid4()),
            speaker="assistant",
            sourceLanguage=lang_name,
            originalText=text,
            translatedText=text,
            confidence=1.0,
            timestamp=now,
        )
        self.transcript_history.append(item.model_dump())
        self.last_translated_text = text
        self.last_language_code = lang_code
        payload = {
            "type": "transcript",
            "item": item.model_dump(),
            "entities": {},
            "actionChips": [],
        }
        if settings.ai_async_tts:
            payload["assistantTtsText"] = text
            payload["assistantTtsLanguageCode"] = lang_code
        else:
            payload["assistantAudio"] = audio_b64
        return payload

    async def build_tts_audio_message(self, text: str, language_code: str | None = None) -> dict:
        """Create a standalone TTS message for delayed audio playback."""
        lang_code = self._supported_language_code(language_code)
        return {
            "type": "tts_audio",
            "audio_b64": await self._call_sarvam_tts(text, lang_code),
            "text": text,
        }

    async def start_customer_session(self) -> dict:
        """Greet the customer after the kiosk mic is pressed once."""
        lang_code = self._supported_language_code(self.detected_language_code)
        text = await self._localized_phrase("greeting", lang_code)
        return await self.build_assistant_message(text, lang_code)

    # ── Sarvam: Text-to-Text Translation ─────────────────────────────────────
    async def _call_sarvam_translate(self, text: str, source_code: str, target_code: str = "en-IN") -> str:
        """Translate text using Sarvam's Translate API. Chunks long text to avoid 400 errors."""
        if not settings.sarvam_api_key or not text:
            return text

        # Sarvam translate has a ~900 char limit; chunk if needed
        max_chunk = 800
        if len(text) <= max_chunk:
            return await self._translate_chunk(text, source_code, target_code)

        # Split at sentence boundaries
        sentences = re.split(r'(?<=[.।!?\n])\s*', text)
        chunks: list[str] = []
        current = ""
        for sentence in sentences:
            if len(current) + len(sentence) > max_chunk and current:
                chunks.append(current.strip())
                current = sentence
            else:
                current = f"{current} {sentence}" if current else sentence
        if current.strip():
            chunks.append(current.strip())

        translated_parts = []
        for chunk in chunks:
            translated_parts.append(await self._translate_chunk(chunk, source_code, target_code))
        return " ".join(translated_parts)

    async def _translate_chunk(self, text: str, source_code: str, target_code: str) -> str:
        """Translate a single chunk of text."""
        try:
            resp = await self.http.post(
                f"{SARVAM_BASE}/translate",
                json={
                    "input": text[:900],
                    "source_language_code": source_code,
                    "target_language_code": target_code,
                    "model": "mayura:v1",
                },
                headers=self.sarvam_headers,
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("translated_text", text)
        except Exception as e:
            logger.error("Sarvam translation failed: %s", e)
            return text

    # ── Sarvam: LLM (Chat) ───────────────────────────────────────────────────
    async def _call_sarvam_llm(self, prompt: str, system_prompt: str = "You are a helpful banking assistant.") -> str:
        """General purpose LLM call using Sarvam Chat API."""
        if not settings.sarvam_api_key:
            return ""

        try:
            resp = await self.http.post(
                f"{SARVAM_BASE}/v1/chat/completions",
                json={
                    "model": "sarvam-m",
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.1,
                },
                headers=self.sarvam_headers,
            )
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            # Robustly strip <think> blocks even if truncated
            original_content = content
            if "</think>" in content:
                content = content.split("</think>")[-1]
            elif "<think>" in content:
                content = content.split("<think>")[0]
            
            result = content.strip()
            if not result:
                # If everything was stripped (e.g. only reasoning), fallback to the original content
                result = original_content.replace("<think>", "").replace("</think>", "").strip()
            return result
        except Exception as e:
            logger.error("Sarvam LLM failed: %s", e)
            return ""

    # ── LLM: Entity Extraction ────────────────────────────────────────────
    async def _extract_entities(self, text: str) -> dict:
        """Extract banking entities from conversation text using Sarvam LLM."""
        fast_entities = self._fast_extract_entities(text)
        if settings.ai_fast_mode or not settings.sarvam_api_key:
            return fast_entities

        prompt = (
            "Extract banking entities from this customer conversation text. "
            "Return ONLY valid JSON with these keys (use empty string if not found): "
            "customerName, pan, phone, accountType, product, amount, cardLast4.\n\n"
            f"Text: {text}"
        )
        try:
            raw = await self._call_sarvam_llm(prompt, "Return only valid JSON.")
            # Strip markdown code fences if present
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()
            entities = json.loads(raw)
            return {**fast_entities, **{k: v for k, v in entities.items() if v}}
        except Exception:
            return fast_entities

    # ── LLM: Action Chip Suggestions ──────────────────────────────────────
    async def _suggest_actions(self, text: str) -> list[str]:
        """Suggest contextual action buttons for the bank teller using Sarvam LLM."""
        fast_actions = self._fast_suggest_actions(text)
        if settings.ai_fast_mode or not settings.sarvam_api_key:
            return fast_actions

        prompt = (
            "Given this banking customer conversation, suggest 2-4 quick action buttons "
            "for the bank teller. Return ONLY a JSON array of short action labels.\n\n"
            f"Text: {text}"
        )
        try:
            raw = await self._call_sarvam_llm(prompt, "Return only a JSON array of strings.")
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()
            actions = json.loads(raw)
            return actions if actions else fast_actions
        except Exception as e:
            logger.error("Sarvam action suggestion failed: %s", e)
            return fast_actions

    def _fast_extract_entities(self, text: str) -> dict:
        """Low-latency deterministic extraction for live UI responsiveness."""
        entities: dict = {}
        pan = re.search(r"\b[A-Z]{5}\d{4}[A-Z]\b", text.upper())
        if pan:
            entities["pan"] = pan.group(0)

        phone = re.search(r"\b(?:\+91[-\s]?)?[6-9]\d{9}\b", text)
        if phone:
            entities["phone"] = re.sub(r"\D", "", phone.group(0))[-10:]

        amount = re.search(r"(?:₹|rs\.?|inr)\s*[\d,]+(?:\.\d+)?(?:\s*(?:lakh|lac|crore))?", text, flags=re.IGNORECASE)
        if amount:
            entities["amount"] = amount.group(0)

        last4 = re.search(r"(?:last\s*(?:four|4)|ending|ends?\s*with)\D*(\d{4})\b", text, flags=re.IGNORECASE)
        if last4:
            entities["cardLast4"] = last4.group(1)

        name = re.search(
            r"(?:my name is|i am|i'm|this is|name is|mera naam|mera name|माझे नाव|माझं नाव|मेरा नाम)\s+([A-Za-z][A-Za-z.'-]*(?:\s+[A-Za-z][A-Za-z.'-]*){0,3})",
            text,
            flags=re.IGNORECASE,
        )
        if name:
            entities["customerName"] = " ".join(part.capitalize() for part in name.group(1).split())

        lowered = text.lower()
        if "savings" in lowered or "saving" in lowered or "सेव्हिंग" in lowered:
            entities["accountType"] = "Savings"
        elif "current account" in lowered:
            entities["accountType"] = "Current"
        elif "salary" in lowered:
            entities["accountType"] = "Salary"

        if "fixed deposit" in lowered or re.search(r"\bfd\b", lowered) or "फिक्स" in lowered:
            entities["product"] = "Fixed Deposit"
        elif "personal loan" in lowered or "loan" in lowered or "कर्ज" in lowered:
            entities["product"] = "Loan"
        elif "credit card" in lowered:
            entities["product"] = "Credit Card"
        elif "debit card" in lowered or "card" in lowered:
            entities["product"] = "Card"
        elif "kyc" in lowered or "केवायसी" in lowered:
            entities["product"] = "KYC"
        return entities

    def _fast_suggest_actions(self, text: str) -> list[str]:
        lowered = text.lower()
        if "fixed deposit" in lowered or re.search(r"\bfd\b", lowered) or "interest" in lowered or "rate" in lowered or "व्याज" in lowered or "मुदत ठेव" in lowered or "सावधि जमा" in lowered:
            return ["Show FD Rates", "Explain FD Documents", "Start Fixed Deposit Form"]
        if "open account" in lowered or "savings account" in lowered or "new account" in lowered or "खाते" in lowered or "खाता" in lowered or "बचत" in lowered:
            return ["Explain Account Documents", "Start Account Opening Form", "Check KYC Rules"]
        if "kyc" in lowered or "aadhaar" in lowered or "aadhar" in lowered or "pan" in lowered or "address update" in lowered or "केवायसी" in lowered or "आधार" in lowered:
            return ["Check KYC Documents", "Start KYC Form", "Verify Identity"]
        if ("lost" in lowered or "block" in lowered or "हरव" in lowered or "खो" in lowered) and ("card" in lowered or "कार्ड" in lowered):
            return ["Block Card", "Read Card Charges", "Raise Dispute"]
        if "card" in lowered or "debit" in lowered or "credit" in lowered or "कार्ड" in lowered:
            return ["Read Card Charges", "Start Card Form", "Check Delivery Rules"]
        if "loan" in lowered or "कर्ज" in lowered or "लोन" in lowered or "ऋण" in lowered:
            return ["Check Loan Eligibility", "Read Rate Disclosure", "Start Loan Application"]
        if "fee" in lowered or "fees" in lowered or "charge" in lowered or "charges" in lowered or "फी" in lowered:
            return ["Read Fee Disclosure", "Show Service Charges", "Check CBS"]
        return ["Search Policy", "Continue Conversation"]

    # ── Sarvam: Compliance Check ─────────────────────────────────────────────
    async def check_compliance(self, text: str) -> ComplianceAlert | None:
        """Check for mis-selling or compliance violations using Sarvam LLM."""
        keyword_alert = self._keyword_compliance(text)
        if keyword_alert or settings.ai_fast_mode or not settings.sarvam_api_key:
            return keyword_alert

        try:
            prompt = (
                "You are an RBI compliance checker for Indian bank staff conversations. "
                "Analyze this staff statement for compliance violations:\n"
                "- Guaranteed returns on mutual funds or market-linked products\n"
                "- Risk-free investment promises\n"
                "- Unauthorized fee waivers\n"
                "- Misleading product comparisons\n\n"
                "Return ONLY valid JSON: {\"compliant\": true/false, \"violation\": \"description or null\"}\n\n"
                f"Statement: {text}"
            )
            raw = await self._call_sarvam_llm(prompt, "Return only valid JSON.")
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()
            result = json.loads(raw)
            if not result.get("compliant", True):
                return ComplianceAlert(
                    severity="block",
                    message=result.get("violation", "Potential compliance violation detected."),
                )
            return None
        except Exception:
            return self._keyword_compliance(text)

    def _keyword_compliance(self, text: str) -> ComplianceAlert | None:
        """Keyword fallback when the Sarvam compliance check is unavailable."""
        restricted = ["guaranteed return", "risk free mutual fund", "no charges ever"]
        lowered = text.lower()
        if any(term in lowered for term in restricted):
            return ComplianceAlert(
                severity="block",
                message="Potential mis-selling phrase detected. Voice output is halted until the statement is corrected.",
            )
        return None

    # ── Sarvam: Sentiment Analysis ───────────────────────────────────────────
    async def _analyze_sentiment(self, text: str) -> SentimentResult:
        """Analyze customer sentiment for escalation detection using Sarvam LLM."""
        fast_sentiment = self._fast_sentiment(text)
        if settings.ai_fast_mode or not settings.sarvam_api_key:
            return fast_sentiment

        try:
            prompt = (
                "Analyze the sentiment of this banking customer statement. "
                "Return ONLY valid JSON: {\"sentiment\": \"negative\"|\"neutral\"|\"positive\", \"score\": 0.0-1.0} "
                "where 0.0 is most negative and 1.0 is most positive.\n\n"
                f"Text: {text}"
            )
            raw = await self._call_sarvam_llm(prompt, "Return only valid JSON.")
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()
            data = json.loads(raw)
            return SentimentResult(
                sentiment=data.get("sentiment", "neutral"),
                score=data.get("score", 0.5),
            )
        except Exception:
            return fast_sentiment

    def _fast_sentiment(self, text: str) -> SentimentResult:
        lowered = text.lower()
        if any(term in lowered for term in NEGATIVE_SENTIMENT_TERMS):
            return SentimentResult(sentiment="negative", score=0.22)
        if any(term in lowered for term in POSITIVE_SENTIMENT_TERMS):
            return SentimentResult(sentiment="positive", score=0.82)
        return SentimentResult(sentiment="neutral", score=0.55)

    # ── Sarvam: Summarize ────────────────────────────────────────────────────
    async def summarize(self, transcript: list[dict] | None = None) -> dict:
        """Generate bilingual session summary using Sarvam LLM."""
        history = transcript or self.transcript_history
        if not history:
            return self._demo_summary()

        try:
            conversation = "\n".join(
                f"[{t.get('speaker', 'unknown')}] {t.get('originalText', '')} → {t.get('translatedText', '')}"
                for t in history
            )
            lang = self.detected_language or LANGUAGE_NAMES.get(self._supported_language_code(self.detected_language_code), "English")
            prompt = (
                f"Summarize this banking conversation as 3-5 bullet points. "
                f"Provide the summary in two sections:\n"
                f"1. English bullet points\n"
                f"2. {lang} bullet points (same content translated)\n\n"
                f"Return ONLY valid JSON: {{\"english\": [\"...\"], \"customerLanguage\": [\"...\"]}}\n\n"
                f"Conversation:\n{conversation}"
            )
            raw = await self._call_sarvam_llm(prompt, "Return only valid JSON.")
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()
            data = json.loads(raw)
            return {
                "type": "summary",
                "english": data.get("english", []),
                "customerLanguage": data.get("customerLanguage", []),
            }
        except Exception as e:
            logger.error("Sarvam summarization failed: %s", e)
            return self._demo_summary()

    def _demo_summary(self) -> dict:
        return {
            "type": "summary",
            "english": [
                "Customer reported a lost credit card and requested immediate blocking.",
                "Staff must verify identity and last four card digits before confirming the block.",
                "Replacement card fee and dispute window should be disclosed in the customer's selected language.",
            ],
            "customerLanguage": [
                "ग्राहकाने क्रेडिट कार्ड हरवल्याची माहिती दिली आणि ते ब्लॉक करण्याची विनंती केली.",
                "ब्लॉक करण्यापूर्वी ओळख आणि कार्डचे शेवटचे चार अंक तपासणे आवश्यक आहे.",
                "नवीन कार्ड शुल्क आणि व्यवहार तक्रार कालावधी मराठीत सांगावा.",
            ],
        }

    # ── Main Turn Processor ──────────────────────────────────────────────────
    async def process_audio_turn(self, audio: bytes, mode: str) -> dict:
        """Full pipeline: STT → translate → extract entities → suggest actions."""
        # 1. Speech-to-Text via Sarvam (Native Transcribe + auto language detection)
        #
        # Staff mode: always en-IN — bank employees speak English and this gives
        # the best ASR quality for that use-case.
        #
        # Customer mode: use the language already detected from a previous turn if
        # available.  On the very first turn pass "unknown" which is Sarvam saaras
        # v3's documented auto-detect sentinel.  Passing None previously fell
        # through _supported_language_code → DEFAULT_LANGUAGE_CODE (mr-IN),
        # biasing the first transcript toward Marathi even for English speakers.
        if mode == "staff":
            stt_lang_hint = "en-IN"
        elif self.detected_language_code:
            stt_lang_hint = self.detected_language_code   # already confirmed from prior turn
        else:
            stt_lang_hint = "unknown"                     # request auto-detect from Sarvam
        stt_result = await self._call_sarvam_stt(audio, stt_lang_hint)

        lang_detected = None
        if self.detected_language is None:
            lang_detected = self._language_info_from_code(stt_result.get("language_code"))
            self.detected_language = lang_detected["language"]
            self.detected_language_code = lang_detected["code"]

        if not stt_result["transcript"]:
            if mode == "customer":
                lang_code = self._supported_language_code(self.detected_language_code or stt_result.get("language_code"))
                text = await self._localized_phrase("repeat_service", lang_code)
                payload = await self.build_assistant_message(text, lang_code)
                if lang_detected:
                    payload["languageDetected"] = lang_detected
                return payload
            return {
                "type": "asr_status",
                "mode": "staff",
                "status": "ignored",
                "message": "No clear staff speech detected. Please try again.",
            }

        original_text = stt_result["transcript"]
        if mode == "customer" and self._is_echo_or_spam_text(original_text):
            lang_code = self._supported_language_code(self.detected_language_code or stt_result.get("language_code"))
            text = await self._localized_phrase("repeat_brief", lang_code)
            payload = await self.build_assistant_message(text, lang_code)
            if lang_detected:
                payload["languageDetected"] = lang_detected
            return payload

        source_code = stt_result["language_code"]
        now = datetime.now().strftime("%H:%M")

        # 2. Translate via Sarvam (Text-to-Text)
        if mode == "customer" and source_code != "en-IN":
            translated = await self._call_sarvam_translate(original_text, source_code, "en-IN")
            speaker = "customer"
            language = self.detected_language or LANGUAGE_NAMES.get(self._supported_language_code(source_code), "English")
        elif mode == "staff":
            # Staff speaks English, translate to customer's native language for display
            target_code = self._supported_language_code(self.detected_language_code)
            translated = await self._call_sarvam_translate(original_text, "en-IN", target_code)
            speaker = "staff"
            language = "English"
        else:
            translated = original_text
            speaker = "customer"
            language = "English"

        # Update last translated text for TTS replay
        self.last_translated_text = translated
        self.last_language_code = self._supported_language_code(self.detected_language_code or source_code)

        # 3. Extract entities from the English text
        # If customer spoke a non-English language, entities come from the translation
        # If staff spoke English, entities come from the original
        english_text = translated if mode == "customer" else original_text

        # ── Parallel enrichment: entities + actions run concurrently ──
        entities_task = asyncio.create_task(self._extract_entities(english_text))
        chips_task = asyncio.create_task(self._suggest_actions(english_text))

        # 5. Sentiment analysis for escalation
        sentiment = None
        assistant_response_text = None
        assistant_audio_b64 = None

        if mode == "customer":
            # A. Sentiment (runs in parallel with entities + chips)
            sentiment_task = asyncio.create_task(self._analyze_sentiment(english_text))

            # B. Product/form intent flow. Explain first, then start only after consent.
            lang_code = self.detected_language_code or source_code
            lang_name = self.detected_language or language or LANGUAGE_NAMES.get(self._supported_language_code(lang_code), "English")
            assistant_response_text, result_auto_form = await self._resolve_customer_response(
                original_text,
                english_text,
                lang_code,
                lang_name,
            )

            # Await sentiment that was running in parallel
            sentiment = await sentiment_task
            if sentiment.score < 0.3:
                self.negative_streak += 1
            else:
                self.negative_streak = 0

            # C. Convert response to TTS. In async mode, text goes to the UI first
            # and the WebSocket route sends audio in a follow-up message.
            if not settings.ai_async_tts:
                assistant_audio_b64 = await self._call_sarvam_tts(assistant_response_text, self._supported_language_code(self.detected_language_code))
        else:
            result_auto_form = None

        # Await parallel enrichment tasks
        entities = await entities_task
        chips = await chips_task

        # Override chips for form confirmation flows
        if mode == "customer":
            normalized_check = f"{original_text} {english_text}".lower()
            if self.awaiting_form_confirmation and self.pending_form_type:
                chips = [f"Explain {FORM_TITLES.get(self.pending_form_type, 'Service')}", f"Start {FORM_TITLES.get(self.pending_form_type, 'Form')}"]
            elif self.pending_form_type and result_auto_form:
                chips = [f"Start {FORM_TITLES.get(result_auto_form, 'Form')}"]

        item = TranscriptItem(
            id=str(uuid4()),
            speaker=speaker,
            sourceLanguage=language,
            originalText=original_text,
            translatedText=translated,
            confidence=stt_result["confidence"],
            timestamp=now,
        )

        self.transcript_history.append(item.model_dump())

        result: dict = {
            "type": "transcript",
            "item": item.model_dump(),
            "entities": entities,
            "actionChips": chips,
        }

        if mode == "staff" and translated:
            result["translatedSpeechText"] = translated
            result["translatedSpeechLanguageCode"] = self._supported_language_code(self.detected_language_code)
            result["translatedSpeechAudience"] = "customer"

        if assistant_response_text:
            result["assistantResponse"] = assistant_response_text
            if settings.ai_async_tts:
                result["assistantTtsText"] = assistant_response_text
                result["assistantTtsLanguageCode"] = self._supported_language_code(self.detected_language_code)
            else:
                result["assistantAudio"] = assistant_audio_b64
        if result_auto_form:
            result["autoStartForm"] = result_auto_form

        if lang_detected:
            result["languageDetected"] = lang_detected
        if sentiment:
            result["sentiment"] = sentiment.model_dump()
        if self.negative_streak >= 3:
            result["escalation"] = {
                "type": "escalation_alert",
                "message": f"Customer frustration detected ({self.negative_streak} consecutive negative turns). Consider manager intervention.",
            }

        return result

    async def process_text_turn(self, text: str, mode: str, language_code: str | None = None) -> dict:
        """Process browser speech-recognition text when provider STT is unavailable."""
        if mode == "staff":
            source_code = "en-IN"
            language = "English"
            english_text = text
            translated_text = await self._call_sarvam_translate(
                text,
                "en-IN",
                self.detected_language_code or language_code or DEFAULT_LANGUAGE_CODE,
            )
        else:
            lang_info = self.set_language(language_code or self.detected_language_code or DEFAULT_LANGUAGE_CODE)
            source_code = lang_info["code"]
            language = lang_info["language"]
            if source_code != "en-IN":
                # clean_translation: what Sarvam returned — used for display only.
                # rag_english_text: may be hint-expanded for retrieval — never shown to the customer.
                clean_translation = await self._call_sarvam_translate(text, source_code, "en-IN")
                if self._is_meaningful_translation(clean_translation, text):
                    english_text = clean_translation
                    rag_english_text = clean_translation
                else:
                    # Translation failed — use the raw text for display,
                    # and the structured English hint only for RAG/LLM.
                    clean_translation = text
                    rag_english_text = self._english_hint_for_native_text(text)
                    english_text = rag_english_text  # entities/chips also benefit from the hint
            else:
                clean_translation = text
                english_text = text
                rag_english_text = text
            # Bug-3 fix: TranscriptItem.translatedText must be the human-readable
            # translation, never the RAG-expansion string.
            translated_text = clean_translation

        now = datetime.now().strftime("%H:%M")
        speaker = "staff" if mode == "staff" else "customer"
        item = TranscriptItem(
            id=str(uuid4()),
            speaker=speaker,
            sourceLanguage=language if speaker == "customer" else "English",
            originalText=text,
            translatedText=translated_text,
            confidence=1.0,
            timestamp=now,
        )
        self.transcript_history.append(item.model_dump())

        # ── Parallel enrichment: entities + actions run concurrently ──
        entities_task = asyncio.create_task(self._extract_entities(english_text))
        chips_task = asyncio.create_task(self._suggest_actions(english_text))
        assistant_response_text = None
        assistant_audio_b64 = None
        result_auto_form = None

        if speaker == "customer":
            lang_name = self.detected_language or LANGUAGE_NAMES.get(self._supported_language_code(source_code), "English")
            assistant_response_text, result_auto_form = await self._resolve_customer_response(
                text,
                english_text,
                source_code,
                lang_name,
            )

            if not settings.ai_async_tts:
                assistant_audio_b64 = await self._call_sarvam_tts(assistant_response_text, source_code)

        # Await parallel enrichment tasks
        entities = await entities_task
        chips = await chips_task

        # Override chips for form confirmation flows
        if speaker == "customer":
            if self.awaiting_form_confirmation and self.pending_form_type:
                chips = [f"Explain {FORM_TITLES.get(self.pending_form_type, 'Service')}", f"Start {FORM_TITLES.get(self.pending_form_type, 'Form')}"]
            elif result_auto_form:
                chips = [f"Start {FORM_TITLES.get(result_auto_form, 'Form')}"]

        result: dict = {
            "type": "transcript",
            "item": item.model_dump(),
            "entities": entities,
            "actionChips": chips,
        }
        if speaker == "staff" and translated_text:
            result["translatedSpeechText"] = translated_text
            result["translatedSpeechLanguageCode"] = self._supported_language_code(self.detected_language_code or language_code)
            result["translatedSpeechAudience"] = "customer"
        if assistant_response_text:
            result["assistantResponse"] = assistant_response_text
            if settings.ai_async_tts:
                result["assistantTtsText"] = assistant_response_text
                result["assistantTtsLanguageCode"] = source_code
            else:
                result["assistantAudio"] = assistant_audio_b64
        if result_auto_form:
            result["autoStartForm"] = result_auto_form
        return result

    async def _resolve_customer_response(
        self,
        native_text: str,
        english_text: str,
        lang_code: str,
        lang_name: str,
    ) -> tuple[str, str | None]:
        """Choose between policy Q&A and form flow for one customer turn."""
        normalized = f"{native_text} {english_text}".lower()
        intent_form = self._detect_form_intent(normalized)
        is_info_request = self._is_info_request(normalized)
        non_form_topic = self._detect_non_form_topic(normalized)
        result_auto_form = None

        if self.awaiting_form_confirmation and self.pending_form_type:
            if self._is_affirmative(normalized):
                response = await self._localized_phrase(
                    "starting_form",
                    lang_code,
                    form_title=FORM_TITLES.get(self.pending_form_type, "banking"),
                )
                result_auto_form = self.pending_form_type
                self.awaiting_form_confirmation = False
                self.pending_form_type = None
                return response, result_auto_form

            if self._is_negative(normalized):
                self.awaiting_form_confirmation = False
                self.pending_form_type = None
                return await self._localized_phrase("no_problem", lang_code), None

            if non_form_topic:
                # Bug-1 fix: only pass english_text to RAG when it's a genuine
                # translation; fall back to a structured English hint otherwise.
                rag_query = (
                    english_text
                    if self._is_meaningful_translation(english_text, native_text)
                    else self._english_hint_for_native_text(native_text)
                )
                rag_answer = await self._rag_customer_answer(rag_query, lang_code)
                if self._has_policy_answer(rag_answer):
                    self.awaiting_form_confirmation = False
                    self.pending_form_type = None
                    return rag_answer, None

            if is_info_request:
                target_form = intent_form or self.pending_form_type
                if intent_form and intent_form != self.pending_form_type:
                    self.pending_form_type = intent_form
                return await self._localized_product_explanation(target_form), None

            if intent_form:
                self.pending_form_type = intent_form
                return await self._localized_product_explanation(intent_form), None

            return await self._localized_phrase("form_yes_no", lang_code), None

        # Bug-2 fix: always run RAG first, before form-intent logic can steal the
        # turn.  A confident KB answer wins unconditionally — form flow is only
        # entered when RAG has nothing useful to say.
        rag_query = (
            english_text
            if self._is_meaningful_translation(english_text, native_text)
            else self._english_hint_for_native_text(native_text)
        )
        rag_answer = await self._rag_customer_answer(rag_query, lang_code)
        if self._has_policy_answer(rag_answer):
            # RAG answered the policy question — return it directly.
            # If the customer also has a form intent (e.g. "open account") and
            # is not merely asking for info, prime the confirmation state so the
            # next turn can start the form without repeating the explainer.
            if intent_form and not is_info_request:
                self.pending_form_type = intent_form
                self.awaiting_form_confirmation = True
                # Append a localised "would you like to start the form?" prompt
                # so the assistant naturally transitions from the policy answer
                # into offering the form.
                start_offer = await self._localized_text(
                    "Would you like me to start the form now?", lang_code
                )
                return f"{rag_answer} {start_offer}", None
            return rag_answer, None

        # RAG found nothing useful — fall through to form-intent / LLM flow.
        if intent_form and not is_info_request:
            self.pending_form_type = intent_form
            self.awaiting_form_confirmation = True
            return await self._localized_product_explanation(intent_form), None

        if intent_form:
            self.pending_form_type = intent_form
            self.awaiting_form_confirmation = True
            return await self._localized_product_explanation(intent_form), None

        # LLM fallback — same Bug-1 guard: English query only.
        # NOTE: Previously this was gated by `not settings.ai_fast_mode`, which
        # caused every unrecognised query to return the generic "help_services"
        # message.  The LLM fallback is now always attempted when the Sarvam API
        # key is configured, ensuring the kiosk gives contextual answers.
        llm_query = (
            english_text
            if self._is_meaningful_translation(english_text, native_text)
            else self._english_hint_for_native_text(native_text)
        )
        response = await self._llm_customer_fallback(llm_query, lang_code, lang_name)
        if response:
            return response, None
        return await self._localized_phrase("help_services", lang_code), None

    async def _llm_customer_fallback(self, english_text: str, lang_code: str, lang_name: str) -> str:
        prompt = (
            f"Customer question: '{english_text}'\n"
            f"Original language: {lang_name} ({lang_code})\n\n"
            "You are a knowledgeable bank branch assistant. Answer this banking question "
            "clearly, accurately, and helpfully in 2-3 sentences. Cover the key facts: "
            "eligibility, documents needed, charges, timelines, or rules as applicable. "
            "If you are not sure about specific rates or numbers, say 'please check with the branch staff for exact details'. "
            f"Respond in {lang_name} language. Be warm and professional."
        )
        return await self._call_sarvam_llm(
            prompt,
            f"You are VoxAssist, an expert Indian bank branch assistant. "
            f"You know about all banking services: accounts, FDs, RDs, loans, cards, lockers, "
            f"cheques, NEFT/RTGS/IMPS, PPF, KYC, insurance, nominations, ATM services, "
            f"net banking, and government schemes. Answer in {lang_name}.",
        )

    def _detect_form_intent(self, english_text: str) -> str | None:
        lowered = english_text.lower()
        for form_type, keywords in FORM_INTENT_KEYWORDS.items():
            if any(keyword in lowered for keyword in keywords):
                return form_type
        return None

    def _detect_non_form_topic(self, text: str) -> str | None:
        lowered = text.lower()
        for topic, keywords in NON_FORM_TOPIC_KEYWORDS.items():
            if any(keyword in lowered for keyword in keywords):
                return topic
        return None

    def _is_affirmative(self, english_text: str) -> bool:
        return self._has_confirmation_term(english_text, AFFIRMATIVE_TERMS)

    def _is_negative(self, english_text: str) -> bool:
        return self._has_confirmation_term(english_text, NEGATIVE_TERMS)

    def _has_confirmation_term(self, text: str, terms: set[str]) -> bool:
        normalized = re.sub(r"[^\w\s'\u0900-\u0D7F]", " ", text.lower(), flags=re.UNICODE)
        normalized = re.sub(r"\s+", " ", normalized).strip()
        padded = f" {normalized} "
        tokens = set(normalized.split())
        for term in terms:
            normalized_term = re.sub(r"[^\w\s'\u0900-\u0D7F]", " ", term.lower(), flags=re.UNICODE)
            normalized_term = re.sub(r"\s+", " ", normalized_term).strip()
            if not normalized_term:
                continue
            if " " in normalized_term:
                if f" {normalized_term} " in padded:
                    return True
            elif normalized_term in tokens:
                return True
        return False

    def _is_info_request(self, text: str) -> bool:
        lowered = text.lower()
        return any(term in lowered for term in INFO_REQUEST_TERMS)

    def _has_policy_answer(self, answer: str | None) -> bool:
        if not answer or len(answer.strip()) <= 10:
            return False
        lowered = answer.lower()
        return "could not find" not in lowered and "not found" not in lowered

    async def _localized_product_explanation(self, form_type: str) -> str:
        explanation = PRODUCT_EXPLAINERS.get(
            form_type,
            "I can help with this banking service. Would you like me to start the form now?",
        )
        lang_code = self.detected_language_code or "en-IN"
        rag_query = (
            f"Explain {FORM_TITLES.get(form_type, form_type)} including current rates, fees, "
            "eligibility, document requirements, branch rules, and whether the customer should start the form."
        )
        rag_answer = await self._rag_customer_answer(rag_query, lang_code)
        if rag_answer and "could not find" not in rag_answer.lower():
            return f"{rag_answer} {await self._localized_text('Would you like me to start the form now?', lang_code)}"
        if lang_code.startswith("mr"):
            return PRODUCT_EXPLAINERS_MR.get(form_type, explanation)
        if lang_code != "en-IN":
            translated = await self._call_sarvam_translate(explanation, "en-IN", lang_code)
            if translated and translated != explanation:
                return translated
        return explanation

    async def _rag_customer_answer(self, query: str, lang_code: str) -> str:
        normalized_query = self._normalize_customer_query_for_rag(query)
        result = await rag_service.answer(
            normalized_query,
            branch_id=self.branch_id,
            language_code=lang_code,
            llm=self._call_sarvam_llm if settings.rag_use_llm and settings.sarvam_api_key else None,
            translate=self._call_sarvam_translate if settings.sarvam_api_key else None,
        )
        return self._localize_rag_answer_without_provider(result, normalized_query, lang_code)

    def _normalize_customer_query_for_rag(self, text: str) -> str:
        lowered = text.lower()
        cheque_terms = ("cheque", "check", "चेक", "धनादेश")
        bounce_terms = (
            "bounce", "bounced", "return", "returned", "insufficient", "बाउन्स", "बाउंस",
            "परत", "रिटर्न", "वटला नाही", "अपुरी शिल्लक",
        )
        if any(term in lowered for term in cheque_terms) and any(term in lowered for term in bounce_terms):
            return f"{text} cheque bounce cheque return insufficient funds charges drawer payee CIBIL"
        if "stop cheque" in lowered or "stop payment" in lowered:
            return f"{text} cheque stop payment charges"
        return text

    def _localize_rag_answer_without_provider(self, result: SopResult, query: str, lang_code: str) -> str:
        """Return the RAG answer, passing it through unchanged.

        Bug-7 fix: the previous implementation short-circuited the entire
        RAG + LLM pipeline for Marathi cheque-bounce queries by returning a
        hardcoded string with stale charge figures (INR 150–750).  Any update
        to the KB would have been silently ignored.

        The function now always returns result.answer so that:
        - Actual KB content (including updated charges) is shown.
        - The LLM translation pipeline in rag_service can still localise the
          answer into Marathi when rag_use_llm / translate are enabled.
        - If the KB already stored a Marathi answer (Devanagari detected) it
          is returned as-is without an unnecessary second translation pass.
        """
        return result.answer

    async def _localized_text(self, english_text: str, lang_code: str) -> str:
        code = self._supported_language_code(lang_code)
        key_by_prefix = {
            "No problem": "no_problem",
            "Please say yes": "form_yes_no",
            "I can help": "help_services",
        }
        for prefix, key in key_by_prefix.items():
            if english_text.startswith(prefix):
                return await self._localized_phrase(key, code)
        if code != "en-IN":
            translated = await self._call_sarvam_translate(english_text, "en-IN", code)
            if translated and translated != english_text:
                return translated
        return english_text

    def _is_meaningful_translation(self, translated: str, source: str) -> bool:
        """Return True only when `translated` is genuinely different from `source`.

        A translation that Sarvam fails to perform often comes back identical to
        the input (or nearly identical). In that case we must NOT send the native
        text to the English KB — we should use a structured English hint instead.
        """
        if not translated or not source:
            return False
        if translated.strip() == source.strip():
            return False
        # If the translated text still contains >30% Devanagari/Indic code-points
        # the translation almost certainly failed and we should treat it as native.
        indic_chars = sum(1 for c in translated if '\u0900' <= c <= '\u0DFF')
        if len(translated) > 0 and indic_chars / len(translated) > 0.30:
            return False
        return True

    def _english_hint_for_native_text(self, text: str) -> str:
        """Return a plain-English query string for a native-language input.

        This is called only when Sarvam translation either fails outright or
        returns the source string unchanged.  The function is intentionally
        comprehensive so that every common banking query intent produces an
        English string the RAG can match against the English KB chunks.
        """
        lowered = text.lower()

        # 1. RAG normalizer may already expand cheque/stop-payment phrases.
        normalized = self._normalize_customer_query_for_rag(lowered)
        if normalized != lowered:
            return normalized

        # 2. Check all non-form topics first (these produce specific KB queries).
        NON_FORM_HINTS: dict[str, str] = {
            "cheque_services": (
                "cheque bounce return charges insufficient funds stop payment CTS rules"
            ),
            "fund_transfer": (
                "NEFT RTGS IMPS fund transfer charges timelines rules"
            ),
            "locker_services": (
                "bank safe deposit locker charges eligibility documents"
            ),
            "rd_services": (
                "recurring deposit RD interest rate tenure documents"
            ),
            "ppf_services": (
                "PPF public provident fund interest rate rules withdrawal"
            ),
            "insurance": (
                "bank insurance policy ULIP charges documents"
            ),
        }
        non_form_topic = self._detect_non_form_topic(lowered)
        if non_form_topic and non_form_topic in NON_FORM_HINTS:
            return NON_FORM_HINTS[non_form_topic]

        # 3. Check all form intent types.
        FORM_INTENT_HINTS: dict[str, str] = {
            "account_opening": (
                "bank account opening documents required PAN Aadhaar eligibility charges"
            ),
            "fd_application": (
                "fixed deposit FD interest rate tenure documents eligibility charges"
            ),
            "loan_application": (
                "loan application eligibility documents income interest rate processing fee"
            ),
            "kyc": (
                "KYC verification update documents required Aadhaar PAN address proof"
            ),
            "card_application": (
                "debit credit card application documents charges delivery"
            ),
        }
        form_intent = self._detect_form_intent(lowered)
        if form_intent and form_intent in FORM_INTENT_HINTS:
            return FORM_INTENT_HINTS[form_intent]

        # 4. Scan the comprehensive Marathi→English keyword map.
        for marathi_substr, english_query in MARATHI_QUERY_HINT_MAP:
            if marathi_substr in lowered:
                return english_query

        # 5. Generic fallback — at least sends an English string to the RAG
        #    instead of raw Marathi, giving a better chance of a partial match.
        return "banking service information documents charges eligibility"

    def _is_echo_or_spam_text(self, text: str) -> bool:
        normalized = re.sub(r"[^\w\s]", " ", text.lower(), flags=re.UNICODE)
        normalized = re.sub(r"\s+", " ", normalized).strip()
        if not normalized:
            return True

        last_assistant = next(
            (
                item.get("originalText", "")
                for item in reversed(self.transcript_history)
                if item.get("speaker") == "assistant"
            ),
            "",
        )
        if last_assistant:
            assistant_normalized = re.sub(r"[^\w\s]", " ", last_assistant.lower(), flags=re.UNICODE)
            assistant_normalized = re.sub(r"\s+", " ", assistant_normalized).strip()
            if len(normalized) > 8 and normalized in assistant_normalized:
                return True
            if len(assistant_normalized) > 8 and assistant_normalized[:40] in normalized:
                return True

        tokens = normalized.split()
        if len(tokens) < 10:
            return False

        max_repeat = max(tokens.count(token) for token in set(tokens))
        repeated_filler_count = sum(
            normalized.count(phrase)
            for phrase in ("ते हे", "जे आहे", "हे जे", "आहे ते", "this is", "that is", "so this")
        )
        return (max_repeat / len(tokens)) > 0.45 or repeated_filler_count >= 4

    # ── Demo Turn (fallback when no real audio/API) ──────────────────────────
    async def process_demo_turn(self, mode: str, lang_detected: dict | None = None) -> dict:
        now = datetime.now().strftime("%H:%M")
        lang_code = self._supported_language_code(self.detected_language_code)
        lang_name = LANGUAGE_NAMES.get(lang_code, "English")
        if mode == "staff":
            return {
                "type": "asr_status",
                "mode": "staff",
                "status": "ignored",
                "message": "Microphone input is unavailable for staff mode.",
            }
        else:
            text = self._fallback_text("help_services", lang_code)
            translated = "My name is Rahul Patil and I have a savings account."
            speaker = "customer"
            language = lang_name
            entities = {"customerName": "Rahul Patil", "accountType": "Savings"}
            chips = ["Search Policy", "Continue Conversation"]

        self.last_translated_text = translated if mode == "staff" else text
        self.last_language_code = lang_code

        item = TranscriptItem(
            id=str(uuid4()),
            speaker=speaker,
            sourceLanguage=language,
            originalText=text,
            translatedText=translated,
            confidence=1.0,
            timestamp=now,
        )
        self.transcript_history.append(item.model_dump())

        result: dict = {
            "type": "transcript",
            "item": item.model_dump(),
            "entities": entities,
            "actionChips": chips,
        }
        if lang_detected:
            result["languageDetected"] = lang_detected
        return result

    # ── Sarvam: SOP Search ───────────────────────────────────────────────────
    async def search_sop(self, query: str, language_code: str = "en-IN") -> SopResult:
        """Search trusted SOPs and generate a grounded answer."""
        return await rag_service.answer(
            query,
            branch_id=self.branch_id,
            language_code=language_code,
            llm=self._call_sarvam_llm if settings.rag_use_llm and settings.sarvam_api_key else None,
            translate=self._call_sarvam_translate if settings.sarvam_api_key else None,
        )

    # ── TTS Replay ───────────────────────────────────────────────────────────
    async def replay_last(self) -> dict:
        """Generate TTS audio for the last translated text."""
        lang_code = self._supported_language_code(self.last_language_code)
        replay_text = self.last_translated_text or self._fallback_text("no_message", lang_code)
        audio_b64 = await self._call_sarvam_tts(
            replay_text,
            lang_code,
        )
        return {
            "type": "tts_audio",
            "audio_b64": audio_b64,
            "text": replay_text,
        }

    # ══════════════════════════════════════════════════════════════════════════
    # FORM INTERVIEW ENGINE
    # ══════════════════════════════════════════════════════════════════════════

    async def start_form_interview(self, form_type_str: str) -> dict:
        """Initialize a form interview session and return the first question.

        Returns the form definition, first question text, and TTS audio of
        the greeting + first question spoken in the customer's detected language.
        """
        definition = get_form_definition(form_type_str)
        if not definition:
            return {"type": "form_error", "message": f"Unknown form type: {form_type_str}"}

        self.form_session = FormSession(form_type=definition.form_type)
        first_field = definition.field_at(0)
        if not first_field:
            return {"type": "form_error", "message": "Form has no fields."}

        lang_code = self._supported_language_code(self.detected_language_code)
        localized_title = await self._localized_form_title(definition.title, lang_code)
        localized_first_question = await self._localized_form_question(first_field.question, lang_code)

        full_question = LOCALIZED_FALLBACKS["en-IN"]["form_intro"].format(
            form_title=definition.title,
            question=first_field.question,
        )
        translated_question = await self._localized_phrase(
            "form_intro",
            lang_code,
            form_title=localized_title,
            question=localized_first_question,
        )

        audio_b64 = await self._call_sarvam_tts(translated_question, lang_code)

        return {
            "type": "form_started",
            "formDefinition": definition.to_dict(),
            "formState": self.form_session.to_dict(),
            "currentField": {
                "key": first_field.key,
                "label": first_field.label,
                "fieldType": first_field.field_type,
                "options": first_field.options,
            },
            "questionText": first_field.question,
            "questionTranslated": translated_question,
            "questionAudio": audio_b64,
        }

    async def process_form_audio_turn(self, audio: bytes) -> dict:
        """Process a single voice answer during an active form interview.

        Pipeline:
        1. STT → get native text
        2. Translate to English
        3. Extract the single field value using LLM
        4. Fill the field, advance to next
        5. Generate TTS for the next question in customer's language
        6. Return updated form state
        """
        if not self.form_session:
            return {"type": "form_error", "message": "No active form interview."}

        definition = FORM_REGISTRY[self.form_session.form_type]
        current_field = definition.field_at(self.form_session.current_field_index)
        if not current_field:
            return {"type": "form_error", "message": "No more fields to fill."}

        # 1. STT + auto-detect language if not yet known
        stt_result = await self._call_sarvam_stt(audio, self.detected_language_code)
        if self.detected_language is None:
            lang_info = self._language_info_from_code(stt_result.get("language_code"))
            self.detected_language = lang_info["language"]
            self.detected_language_code = lang_info["code"]

        if not stt_result["transcript"]:
            # No speech detected — ask again
            lang_code = self._supported_language_code(self.detected_language_code)
            localized_current_question = await self._localized_form_question(current_field.question, lang_code)
            retry_text = LOCALIZED_FALLBACKS["en-IN"]["form_retry"].format(question=current_field.question)
            retry_translated = await self._localized_phrase("form_retry", lang_code, question=localized_current_question)
            audio_b64 = await self._call_sarvam_tts(retry_translated, lang_code)
            return {
                "type": "form_retry",
                "formState": self.form_session.to_dict(),
                "currentField": {
                    "key": current_field.key,
                    "label": current_field.label,
                    "fieldType": current_field.field_type,
                    "options": current_field.options,
                },
                "questionText": retry_text,
                "questionTranslated": retry_translated,
                "questionAudio": audio_b64,
            }

        native_text = stt_result["transcript"]
        source_code = stt_result["language_code"]

        # 3. Translate to English for entity extraction
        if source_code != "en-IN":
            english_text = await self._call_sarvam_translate(native_text, source_code, "en-IN")
        else:
            english_text = native_text

        # 4. Extract the specific field value from the English answer
        extracted_value = await self._extract_form_field(
            english_text, current_field.key, current_field.label,
            current_field.validation_hint, current_field.options
        )

        # 5. Fill the field
        self.form_session.filled_fields[current_field.key] = extracted_value
        filled_field_key = current_field.key
        filled_field_label = current_field.label

        # 6. Advance to next field
        self.form_session.current_field_index += 1
        next_field = definition.field_at(self.form_session.current_field_index)

        if next_field is None:
            # All fields filled!
            self.form_session.is_complete = True
            lang_code = self._supported_language_code(self.detected_language_code)
            localized_title = await self._localized_form_title(definition.title, lang_code)
            completion_text = LOCALIZED_FALLBACKS["en-IN"]["form_complete"].format(form_title=definition.title)
            completion_translated = await self._localized_phrase("form_complete", lang_code, form_title=localized_title)
            audio_b64 = await self._call_sarvam_tts(completion_translated, lang_code)

            return {
                "type": "form_complete",
                "formState": self.form_session.to_dict(),
                "filledFieldKey": filled_field_key,
                "filledFieldLabel": filled_field_label,
                "filledFieldValue": extracted_value,
                "nativeAnswer": native_text,
                "englishAnswer": english_text,
                "completionText": completion_text,
                "completionTranslated": completion_translated,
                "completionAudio": audio_b64,
            }

        # Build confirmation + next question
        lang_code = self._supported_language_code(self.detected_language_code)
        localized_next_question = await self._localized_form_question(next_field.question, lang_code)
        next_question = LOCALIZED_FALLBACKS["en-IN"]["got_it_question"].format(question=next_field.question)
        next_translated = await self._localized_phrase("got_it_question", lang_code, question=localized_next_question)
        audio_b64 = await self._call_sarvam_tts(next_translated, lang_code)

        return {
            "type": "form_field_filled",
            "formState": self.form_session.to_dict(),
            "filledFieldKey": filled_field_key,
            "filledFieldLabel": filled_field_label,
            "filledFieldValue": extracted_value,
            "nativeAnswer": native_text,
            "englishAnswer": english_text,
            "currentField": {
                "key": next_field.key,
                "label": next_field.label,
                "fieldType": next_field.field_type,
                "options": next_field.options,
            },
            "questionText": next_field.question,
            "questionTranslated": next_translated,
            "questionAudio": audio_b64,
        }

    async def process_form_text_turn(self, text: str, mode: str, language_code: str | None = None) -> dict:
        """Text fallback version of process_form_audio_turn. Used when kiosk relies on Web Speech API."""
        if not self.form_session or self.form_session.is_complete:
            return {"type": "error", "message": "No active form session"}

        definition = FORM_REGISTRY[self.form_session.form_type]
        current_field = definition.field_at(self.form_session.current_field_index)
        if not current_field:
            return {"type": "error", "message": "Form already fully answered"}

        if not text.strip():
            # No text provided — ask again
            lang_code = self._supported_language_code(self.detected_language_code or language_code)
            localized_current_question = await self._localized_form_question(current_field.question, lang_code)
            retry_text = LOCALIZED_FALLBACKS["en-IN"]["form_retry"].format(question=current_field.question)
            retry_translated = await self._localized_phrase("form_retry", lang_code, question=localized_current_question)
            audio_b64 = await self._call_sarvam_tts(retry_translated, lang_code)
            return {
                "type": "form_retry",
                "formState": self.form_session.to_dict(),
                "currentField": {
                    "key": current_field.key,
                    "label": current_field.label,
                    "fieldType": current_field.field_type,
                    "options": current_field.options,
                },
                "questionText": retry_text,
                "questionTranslated": retry_translated,
                "questionAudio": audio_b64,
            }

        native_text = text
        source_code = self._supported_language_code(language_code or self.detected_language_code)

        # 3. Translate to English for entity extraction
        if source_code != "en-IN":
            english_text = await self._call_sarvam_translate(native_text, source_code, "en-IN")
        else:
            english_text = native_text

        # 4. Extract the specific field value from the English answer
        extracted_value = await self._extract_form_field(
            english_text, current_field.key, current_field.label,
            current_field.validation_hint, current_field.options
        )

        # 5. Fill the field
        self.form_session.filled_fields[current_field.key] = extracted_value
        filled_field_key = current_field.key
        filled_field_label = current_field.label

        # 6. Advance to next field
        self.form_session.current_field_index += 1
        next_field = definition.field_at(self.form_session.current_field_index)

        if next_field is None:
            # All fields filled!
            self.form_session.is_complete = True
            lang_code = self._supported_language_code(self.detected_language_code or language_code)
            localized_title = await self._localized_form_title(definition.title, lang_code)
            completion_text = LOCALIZED_FALLBACKS["en-IN"]["form_complete"].format(form_title=definition.title)
            completion_translated = await self._localized_phrase("form_complete", lang_code, form_title=localized_title)
            audio_b64 = await self._call_sarvam_tts(completion_translated, lang_code)

            return {
                "type": "form_complete",
                "formState": self.form_session.to_dict(),
                "filledFieldKey": filled_field_key,
                "filledFieldLabel": filled_field_label,
                "filledFieldValue": extracted_value,
                "nativeAnswer": native_text,
                "englishAnswer": english_text,
                "completionText": completion_text,
                "completionTranslated": completion_translated,
                "completionAudio": audio_b64,
            }

        # Build confirmation + next question
        lang_code = self._supported_language_code(self.detected_language_code or language_code)
        localized_next_question = await self._localized_form_question(next_field.question, lang_code)
        next_question = LOCALIZED_FALLBACKS["en-IN"]["got_it_question"].format(question=next_field.question)
        next_translated = await self._localized_phrase("got_it_question", lang_code, question=localized_next_question)

        audio_b64 = await self._call_sarvam_tts(next_translated, lang_code)

        return {
            "type": "form_field_filled",
            "formState": self.form_session.to_dict(),
            "filledFieldKey": filled_field_key,
            "filledFieldLabel": filled_field_label,
            "filledFieldValue": extracted_value,
            "nativeAnswer": native_text,
            "englishAnswer": english_text,
            "currentField": {
                "key": next_field.key,
                "label": next_field.label,
                "fieldType": next_field.field_type,
                "options": next_field.options,
            },
            "questionText": next_field.question,
            "questionTranslated": next_translated,
            "questionAudio": audio_b64,
        }

    async def _extract_form_field(
        self,
        text: str,
        field_key: str,
        field_label: str,
        validation_hint: str,
        options: list[str] | None = None,
    ) -> str:
        """Extract a single form field value from the customer's spoken answer."""
        fast_entities = self._fast_extract_entities(text)
        if field_key in {"full_name", "nominee_name"} and fast_entities.get("customerName"):
            return fast_entities["customerName"]
        if field_key in {"phone", "mobile", "registered_mobile"} and fast_entities.get("phone"):
            return fast_entities["phone"]
        if field_key == "pan_number" and fast_entities.get("pan"):
            return fast_entities["pan"]
        if field_key in {"deposit_amount", "loan_amount", "initial_deposit", "annual_income", "monthly_income", "credit_limit"} and fast_entities.get("amount"):
            return fast_entities["amount"]

        options_str = f" Valid options are: {', '.join(options)}." if options else ""
        prompt = (
            f"The customer was asked for their '{field_label}' and replied: \"{text}\"\n"
            f"Extract ONLY the value for '{field_label}' from this response.{options_str}\n"
        )
        if validation_hint:
            prompt += f"Expected format: {validation_hint}\n"
        prompt += (
            "Return ONLY the extracted value as plain text — no JSON, no quotes, no explanation. "
            "If the answer contains the value along with filler words, extract just the value. "
            "The value must be in English."
        )

        try:
            value = await self._call_sarvam_llm(prompt, "Extract the exact value. Return only the value, nothing else.")
            value = value.strip().strip('"').strip("'")
            if not value:
                return text.strip()
            return value
        except Exception:
            # Fallback: return the English text as-is
            return text.strip()

    def cancel_form_interview(self) -> dict:
        """Cancel the active form interview."""
        self.form_session = None
        return {"type": "form_cancelled"}

    async def generate_form_pdf(self, session_id: str) -> io.BytesIO:
        """Generate a professional PDF for the completed (or partially filled) form."""
        if not self.form_session:
            raise ValueError("No active form session to generate PDF for.")
        if not self.form_session.filled_fields:
            raise ValueError("No fields have been filled yet.")

        from reportlab.lib.colors import Color, HexColor
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import mm
        from reportlab.pdfgen import canvas

        definition = FORM_REGISTRY[self.form_session.form_type]
        buf = io.BytesIO()
        c = canvas.Canvas(buf, pagesize=A4)
        w, h = A4

        # ── Colors ──
        primary = HexColor("#1a237e")       # Deep indigo
        accent = HexColor("#283593")
        light_bg = HexColor("#e8eaf6")
        border = HexColor("#9fa8da")
        text_dark = HexColor("#212121")
        text_muted = HexColor("#616161")
        success = HexColor("#2e7d32")

        # ── Header Bar ──
        c.setFillColor(primary)
        c.rect(0, h - 35 * mm, w, 35 * mm, fill=True, stroke=False)

        c.setFillColor(HexColor("#ffffff"))
        c.setFont("Helvetica-Bold", 20)
        c.drawString(20 * mm, h - 18 * mm, "VoxAssist Banking")
        c.setFont("Helvetica", 11)
        c.drawString(20 * mm, h - 26 * mm, definition.title.upper())

        # Right side — date & session
        c.setFont("Helvetica", 9)
        c.drawRightString(w - 20 * mm, h - 18 * mm, f"Date: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
        c.drawRightString(w - 20 * mm, h - 24 * mm, f"Session: {session_id[:16]}")

        # ── AI Badge ──
        badge_y = h - 45 * mm
        c.setFillColor(success)
        c.roundRect(20 * mm, badge_y - 2 * mm, 60 * mm, 7 * mm, 2 * mm, fill=True, stroke=False)
        c.setFillColor(HexColor("#ffffff"))
        c.setFont("Helvetica-Bold", 8)
        c.drawString(23 * mm, badge_y, "✓  AI VOICE AUTO-FILLED")

        c.setFillColor(text_muted)
        c.setFont("Helvetica", 8)
        c.drawString(85 * mm, badge_y, f"Language: {self.detected_language or 'Auto-detected'}")

        # ── Form Fields Table ──
        y = h - 60 * mm
        row_height = 12 * mm
        label_x = 22 * mm
        value_x = 75 * mm
        col_width_label = 50 * mm
        col_width_value = w - value_x - 20 * mm

        # Table header
        c.setFillColor(accent)
        c.rect(20 * mm, y - 1 * mm, w - 40 * mm, 8 * mm, fill=True, stroke=False)
        c.setFillColor(HexColor("#ffffff"))
        c.setFont("Helvetica-Bold", 9)
        c.drawString(label_x, y + 1.5 * mm, "FIELD")
        c.drawString(value_x, y + 1.5 * mm, "VALUE")

        y -= row_height * 0.6

        # Table rows
        for i, field_def in enumerate(definition.fields):
            value = self.form_session.filled_fields.get(field_def.key, "—")

            # Alternating row background
            if i % 2 == 0:
                c.setFillColor(light_bg)
                c.rect(20 * mm, y - 3 * mm, w - 40 * mm, row_height, fill=True, stroke=False)

            # Border bottom
            c.setStrokeColor(border)
            c.setLineWidth(0.3)
            c.line(20 * mm, y - 3 * mm, w - 20 * mm, y - 3 * mm)

            # Field label
            c.setFillColor(text_dark)
            c.setFont("Helvetica-Bold", 9)
            c.drawString(label_x, y + 2 * mm, field_def.label)

            # Field value
            c.setFont("Helvetica", 10)
            if value and value != "—":
                c.setFillColor(text_dark)
                # Truncate long values
                display_value = value[:60] + ("..." if len(value) > 60 else "")
                c.drawString(value_x, y + 2 * mm, display_value)
                # AI checkmark
                c.setFillColor(success)
                c.setFont("Helvetica", 7)
                c.drawRightString(w - 22 * mm, y + 2 * mm, "✓ AI")
            else:
                c.setFillColor(text_muted)
                c.drawString(value_x, y + 2 * mm, "—")

            y -= row_height

            # Page break if needed
            if y < 40 * mm:
                c.showPage()
                y = h - 30 * mm

        # ── Footer section ──
        y -= 10 * mm

        # Signature box
        c.setStrokeColor(border)
        c.setLineWidth(0.5)
        c.rect(20 * mm, y - 20 * mm, 70 * mm, 20 * mm, fill=False, stroke=True)
        c.setFillColor(text_muted)
        c.setFont("Helvetica", 8)
        c.drawString(22 * mm, y - 17 * mm, "Customer Signature")

        c.rect(w - 90 * mm, y - 20 * mm, 70 * mm, 20 * mm, fill=False, stroke=True)
        c.drawString(w - 88 * mm, y - 17 * mm, "Bank Official Signature")

        # Footer line
        y -= 30 * mm
        c.setStrokeColor(primary)
        c.setLineWidth(1)
        c.line(20 * mm, y, w - 20 * mm, y)
        y -= 5 * mm
        c.setFillColor(text_muted)
        c.setFont("Helvetica", 7)
        c.drawString(20 * mm, y, f"Generated by VoxAssist AI • {datetime.now().strftime('%d %b %Y, %H:%M')} • Session: {session_id}")
        c.drawRightString(w - 20 * mm, y, "This form was auto-filled using AI voice technology.")

        c.save()
        buf.seek(0)
        return buf
