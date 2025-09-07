import datetime
import random
import re
import xml.etree.ElementTree as ET

import httpx
from dash import Input, Output, dcc, html
from loguru import logger

from components.base import BaseComponent
from utils.file_cache import cache_json
from utils.styles import COLORS, FONT_FAMILY

FEEDS = {
    "BBC News": "https://feeds.bbci.co.uk/news/rss.xml",
    "WSJ World News": "https://feeds.a.dj.com/rss/RSSWorldNews.xml",
    "Al Jazeera": "https://www.aljazeera.com/xml/rss/all.xml",
}

CLICKBAIT_PATTERNS = [
    r"\bwhat happened\b",
    r"\byou won'?t believe\b",
    r"\bcould change\b",
    r"\bshocking\b",
    r"\bamazing\b",
    r"\bthis is why\b",
    r"\bnumber \d+\b",
]

COMPLIMENTS = [
    "You look absolutely radiant today!",
    "Your smile could light up the entire room.",
    "You have incredible style and grace.",
    "Your positive energy is contagious!",
    "You're absolutely glowing this morning.",
    "That outfit looks fantastic on you!",
    "You have such beautiful eyes.",
    "Your confidence is inspiring.",
    "You look ready to conquer the day!",
    "Your hair looks amazing today.",
    "You have such a warm and welcoming presence.",
    "You're looking particularly sharp today.",
    "Your creativity knows no bounds.",
    "You have an incredible sense of humor.",
    "You're absolutely brilliant!",
    "Your kindness makes the world a better place.",
    "You have such great taste in everything.",
    "You're looking wonderfully refreshed.",
    "Your passion for life is admirable.",
    "You have the most genuine smile.",
    "You're absolutely stunning today!",
    "Your intelligence is remarkable.",
    "You have such a calming presence.",
    "You're looking incredibly sophisticated.",
    "Your optimism is refreshing.",
    "You have beautiful skin that's practically glowing.",
    "You're absolutely charming!",
    "Your voice has such a lovely tone.",
    "You have incredible posture.",
    "You're looking particularly vibrant today.",
    "Your laugh is absolutely delightful.",
    "You have such expressive eyes.",
    "You're radiating confidence today.",
    "Your sense of style is impeccable.",
    "You have such a graceful way of moving.",
    "You're looking wonderfully put-together.",
    "Your enthusiasm is infectious!",
    "You have the most beautiful complexion.",
    "You're absolutely glowing with health.",
    "Your smile is your best accessory.",
    "You have such elegant features.",
    "You're looking incredibly chic today.",
    "Your energy is absolutely magnetic.",
    "You have such beautiful hands.",
    "You're looking perfectly polished.",
    "Your wit is absolutely sharp.",
    "You have such a lovely aura about you.",
    "You're looking wonderfully serene.",
    "Your style choices are always on point.",
    "You have the most captivating presence.",
    "You're absolutely magnificent today!",
    "Your inner beauty shines through.",
    "You have such a youthful glow.",
    "You're looking incredibly well-rested.",
    "Your fashion sense is extraordinary.",
    "You have such perfect timing.",
    "You're looking absolutely divine.",
    "Your grace under pressure is admirable.",
    "You have such a melodious voice.",
    "You're looking wonderfully composed.",
    "Your creativity is truly inspiring.",
    "You have such beautiful bone structure.",
    "You're absolutely effervescent today!",
    "Your wisdom shines through your eyes.",
    "You have such a regal bearing.",
    "You're looking incredibly polished.",
    "Your authenticity is refreshing.",
    "You have such a warm heart.",
    "You're looking absolutely resplendent.",
    "Your intelligence is captivating.",
    "You have such graceful movements.",
    "You're looking wonderfully relaxed.",
    "Your personality is absolutely magnetic.",
    "You have such beautiful features.",
    "You're looking incredibly stylish today.",
    "Your compassion is truly beautiful.",
    "You have such a lovely speaking voice.",
    "You're absolutely radiant with joy.",
    "Your confidence is incredibly attractive.",
    "You have such perfect proportions.",
    "You're looking wonderfully healthy.",
    "Your sense of humor is delightful.",
    "You have such expressive facial features.",
    "You're looking absolutely flawless today.",
    "Your kindness radiates from within.",
    "You have such beautiful coloring.",
    "You're looking incredibly fresh-faced.",
    "Your sophistication is remarkable.",
    "You have such a lovely complexion.",
    "You're absolutely glowing today!",
    "Your elegance is timeless.",
    "You have such beautiful hair texture.",
    "You're looking wonderfully vibrant.",
    "Your charm is absolutely irresistible.",
    "You have such a peaceful demeanor.",
    "You're looking incredibly well-groomed.",
    "Your spirit is absolutely beautiful.",
    "You have such lovely facial symmetry.",
    "You're looking absolutely stunning!",
    "Your grace is truly admirable.",
    "You have such beautiful hands and nails.",
    "You're looking wonderfully confident.",
    "Your aura is absolutely captivating.",
    "You have such expressive eyebrows.",
    "You're looking incredibly polished today.",
    "Your presence lights up any room.",
    "You have such a lovely figure.",
    "You're absolutely glowing with happiness.",
    "Your style is effortlessly chic.",
    "You have such beautiful facial features.",
    "You're looking wonderfully serene today.",
    "Your energy is absolutely infectious.",
    "You have such a lovely smile lines.",
    "You're looking incredibly put-together.",
    "Your beauty is absolutely timeless.",
    "You have such graceful hand gestures.",
    "You're looking wonderfully relaxed today.",
    "Your confidence is absolutely stunning.",
    "You have such beautiful skin tone.",
    "You're absolutely radiant this morning!",
    "Your elegance is truly exceptional.",
    "You have such lovely facial expressions.",
    "You're looking incredibly sophisticated.",
    "Your charm is absolutely delightful.",
    "You have such beautiful eye color.",
    "You're looking wonderfully refreshed today.",
    "Your grace under any situation is admirable.",
    "You have such a lovely neck and shoulders.",
    "You're absolutely glowing with vitality.",
    "Your style choices are always perfect.",
    "You have such expressive and kind eyes.",
    "You're looking incredibly well today.",
    "Your presence is absolutely magnetic.",
    "You have such beautiful facial structure.",
    "You're looking wonderfully composed today.",
    "Your inner light shines so brightly.",
    "You have such a lovely way of carrying yourself.",
    "You're absolutely stunning in every way!",
    "Your confidence is truly inspiring.",
    "You have such beautiful natural coloring.",
    "You're looking incredibly fresh today.",
    "Your elegance is absolutely captivating.",
    "You have such a warm and inviting smile.",
    "You're looking wonderfully polished today.",
    "Your beauty radiates from the inside out.",
    "You have such graceful and elegant posture.",
    "You're absolutely glowing with inner peace.",
    "Your style is effortlessly sophisticated.",
    "You have such beautiful and expressive features.",
    "You're looking incredibly vibrant today!",
    "Your presence brings joy to everyone around you.",
    "You have such a lovely and melodic laugh.",
    "You're absolutely radiant with confidence.",
    "Your grace and poise are truly remarkable.",
    "You have such beautiful and healthy-looking skin.",
    "You're looking wonderfully put-together today.",
    "Your charm and wit are absolutely delightful.",
    "You have such expressive and intelligent eyes.",
    "You're absolutely glowing with happiness today!",
    "Your elegance and sophistication are timeless.",
    "You have such a lovely and calming presence.",
    "You're looking incredibly well-rested today.",
    "Your confidence and grace are truly inspiring.",
    "You have such beautiful and delicate features.",
    "You're absolutely stunning in the morning light!",
    "Your style and fashion sense are impeccable.",
    "You have such a warm and genuine personality.",
    "You're looking wonderfully serene and peaceful.",
    "Your beauty and grace are absolutely captivating.",
    "You have such lovely and expressive facial features.",
    "You're absolutely radiant with joy and vitality!",
    "Your confidence and poise are truly remarkable.",
    "You have such beautiful and healthy-looking hair.",
    "You're looking incredibly sophisticated today.",
    "Your charm, wit, and intelligence are delightful.",
    "You have such expressive and beautiful eyes.",
    "You're absolutely glowing with inner beauty today!",
    "Your elegance and grace are truly exceptional.",
    "You have such a lovely and infectious personality.",
    "You're looking wonderfully refreshed and vibrant.",
    "Your confidence and natural beauty are inspiring.",
    "You have such beautiful and delicate bone structure.",
    "You're absolutely stunning in every possible way!",
    "Your style, grace, and elegance are timeless.",
    "You have such a warm, kind, and beautiful soul.",
    "You're looking incredibly well and absolutely radiant!",
    "Your presence, charm, and beauty light up the world.",
    "You have such lovely features and a captivating smile.",
    "You're absolutely glowing with confidence and grace today!",
    "Your beauty, both inside and out, is truly remarkable.",
    "You have such an elegant way of moving through the world.",
    "You're looking wonderfully polished and absolutely divine!",
    "Your confidence, intelligence, and beauty are inspiring to all.",
]

JOKES = [
    "Why don't scientists trust atoms? Because they make up everything!",
    "I told my wife she was drawing her eyebrows too high. She looked surprised.",
    "Why did the scarecrow win an award? He was outstanding in his field!",
    "I'm reading a book about anti-gravity. It's impossible to put down!",
    "Why don't eggs tell jokes? They'd crack each other up!",
    "What do you call a fake noodle? An impasta!",
    "How do you organize a space party? You planet!",
    "Why did the math book look so sad? Because it had too many problems!",
    "What do you call a bear with no teeth? A gummy bear!",
    "Why did the bicycle fall over? Because it was two-tired!",
    "What's the best thing about Switzerland? I don't know, but the flag is a big plus!",
    "Why don't scientists trust stairs? Because they're always up to something!",
    "What do you call a dinosaur that crashes his car? Tyrannosaurus Wrecks!",
    "Why did the coffee file a police report? It got mugged!",
    "What do you call a sleeping bull? A bulldozer!",
    "Why don't some couples go to the gym? Because some relationships don't work out!",
    "What did one wall say to the other wall? I'll meet you at the corner!",
    "Why did the cookie go to the doctor? Because it felt crumbly!",
    "What do you call a fish wearing a crown? A king fish!",
    "Why did the golfer bring two pairs of pants? In case he got a hole in one!",
    "What's orange and sounds like a parrot? A carrot!",
    "Why don't scientists trust the ocean? Because it's too deep!",
    "What do you call a pig that does karate? A pork chop!",
    "Why did the banana go to the doctor? It wasn't peeling well!",
    "What do you call a cow with no legs? Ground beef!",
    "Why did the tomato turn red? Because it saw the salad dressing!",
    "What do you call a belt made of watches? A waist of time!",
    "Why don't scientists trust pencils? Because they're not 2B trusted!",
    "What do you call a dog magician? A labracadabrador!",
    "Why did the computer go to the doctor? Because it had a virus!",
    "What do you call a sheep with no legs? A cloud!",
    "Why don't scientists trust mirrors? Because they always reflect!",
    "What do you call a fish that needs help with his vocals? Auto-tuna!",
    "Why did the picture go to jail? Because it was framed!",
    "What do you call a dinosaur that loves to sleep? A dino-snore!",
    "Why don't scientists trust elevators? Because they're always up to something!",
    "What do you call a nervous javelin thrower? Shakespeare!",
    "Why did the math teacher call in sick? She had algebra!",
    "What do you call a fake stone in Ireland? A sham rock!",
    "Why don't scientists trust calendars? Because their days are numbered!",
    "What do you call a snowman with a six-pack? An abdominal snowman!",
    "Why did the student eat his homework? Because the teacher told him it was a piece of cake!",
    "What do you call a bear in the rain? A drizzly bear!",
    "Why don't scientists trust keys? Because they always lock things up!",
    "What do you call a cow that plays an instrument? A moo-sician!",
    "Why did the cookie cry? Because its mom was a wafer so long!",
    "What do you call a fish wearing a bowtie? Sofishticated!",
    "Why don't scientists trust clocks? Because time flies!",
    "What do you call a sleeping dinosaur? A dino-snore!",
    "Why did the banana split? Because it couldn't find a spoon!",
    "What do you call a pig that knows karate? A pork chop!",
    "Why don't scientists trust batteries? Because they're always charged!",
    "What do you call a cow with two legs? Lean beef!",
    "Why did the grape stop in the middle of the road? Because it ran out of juice!",
    "What do you call a fish that wears a crown? A king fish!",
    "Why don't scientists trust magnets? Because they're too attractive!",
    "What do you call a sleeping bull? A bulldozer!",
    "Why did the orange stop rolling down the hill? It ran out of juice!",
    "What do you call a pig that does comedy? A ham!",
    "Why don't scientists trust rubber bands? Because they're too stretchy!",
    "What do you call a cow that just gave birth? De-calf-inated!",
    "Why did the apple go to the gym? To get some core strength!",
    "What do you call a fish that's good at volleyball? A net fish!",
    "Why don't scientists trust shoes? Because they always have sole!",
    "What do you call a pig that's cold? A pork-sicle!",
    "Why did the lemon stop rolling? Because it was tired of being squeezed!",
    "What do you call a fish that's a magician? A magic carp!",
    "Why don't scientists trust socks? Because they always disappear!",
    "What do you call a cow that works for a gardener? A lawn moo-er!",
    "Why did the strawberry cry? Because it was in a jam!",
    "What do you call a fish that tells jokes? A clown fish!",
    "Why don't scientists trust pants? Because they're always falling down!",
    "What do you call a pig that's a detective? Sherlock Hams!",
    "Why did the peach go to the doctor? It wasn't feeling peachy!",
    "What do you call a fish that's always complaining? A crab!",
    "Why don't scientists trust hats? Because they always go over your head!",
    "What do you call a cow that's a spy? A cattle-log agent!",
    "Why did the watermelon have a big wedding? Because it cantaloupe!",
    "What do you call a fish that's good at basketball? A slam dunk fish!",
    "Why don't scientists trust gloves? Because they're always covering something up!",
    "What do you call a pig that's a musician? A ham-monic!",
    "Why did the kiwi go to the doctor? It wasn't feeling fruity!",
    "What do you call a fish that's a teacher? A school fish!",
    "Why don't scientists trust shirts? Because they always have something up their sleeve!",
    "What do you call a cow that's always cold? A brrr-ger!",
    "Why did the pineapple stop dancing? Because it was getting dizzy!",
    "What do you call a fish that's a lawyer? A legal eagle fish!",
    "Why don't scientists trust jackets? Because they're always zipped up!",
    "What do you call a pig that's a chef? A ham-burger maker!",
    "Why did the mango go to school? To become more well-rounded!",
    "What do you call a fish that's a doctor? A sturgeon!",
    "Why don't scientists trust scarves? Because they're always wrapped up in something!",
    "What do you call a cow that's a comedian? A laugh-stock!",
    "Why did the papaya go to the gym? To get more a-peel!",
    "What do you call a fish that's a librarian? A book-fish!",
    "Why don't scientists trust ties? Because they're always in a knot!",
    "What do you call a pig that's a pilot? Captain Ham-solo!",
    "Why did the dragon fruit go to the party? To add some fire to the mix!",
    "What do you call a fish that's a photographer? A snap-per!",
    "Why don't scientists trust belts? Because they always hold things together!",
    "What do you call a cow that's a mathematician? A cow-culator!",
    "Why did the passion fruit get excited? Because it found its calling!",
    "What do you call a fish that's a mechanic? A tuna-up specialist!",
    "Why don't scientists trust watches? Because they're always ticking!",
    "What do you call a pig that's a therapist? A ham-pathy expert!",
    "Why did the star fruit shine so bright? Because it was stellar!",
    "What do you call a fish that's a DJ? A bass master!",
    "Why don't scientists trust rings? Because they're always going in circles!",
    "What do you call a cow that's a weather forecaster? A moo-teorologist!",
    "Why did the lychee go to the spa? To get some inner peace!",
    "What do you call a fish that's a dancer? A tango fish!",
    "Why don't scientists trust necklaces? Because they're always hanging around!",
    "What do you call a pig that's a gardener? A ham-green thumb!",
    "Why did the rambutan get a haircut? Because it was looking a bit wild!",
    "What do you call a fish that's a singer? A bass-o profundo!",
    "Why don't scientists trust earrings? Because they're always dangling!",
    "What do you call a cow that's a travel agent? A moo-ving specialist!",
    "Why did the durian clear the room? Because it had a strong personality!",
    "What do you call a fish that's a comedian? A funny fish!",
    "Why don't scientists trust bracelets? Because they're always circling around!",
    "What do you call a pig that's a personal trainer? A ham-strong instructor!",
    "Why did the jackfruit join the gym? To work on its core!",
    "What do you call a fish that's a news anchor? A bass-caster!",
    "Why don't scientists trust anklets? Because they're always at your feet!",
    "What do you call a cow that's a life coach? A moo-tivational speaker!",
    "Why did the breadfruit go to cooking school? To rise to the occasion!",
    "What do you call a fish that's a fashion designer? A style-fish!",
    "Why don't scientists trust pins? Because they're always poking around!",
    "What do you call a pig that's a massage therapist? A ham-assage expert!",
    "Why did the cherimoya meditate? To find inner sweetness!",
    "What do you call a fish that's a real estate agent? A house-fish!",
    "Why don't scientists trust buttons? Because they're always pushing it!",
    "What do you call a cow that's a yoga instructor? A moo-ga teacher!",
    "Why did the soursop smile? Because it was having a sweet day!",
    "What do you call a fish that's a taxi driver? A cab-fish!",
    "Why don't scientists trust zippers? Because they're always opening up!",
    "What do you call a pig that's a barista? A ham-ccino maker!",
    "Why did the ackee feel accomplished? Because it finally cracked the code!",
    "What do you call a fish that's a mail carrier? A post-fish!",
    "Why don't scientists trust snaps? Because they're always fastening things!",
    "What do you call a cow that's a crossing guard? A moo-ving traffic director!",
    "Why did the plantain feel versatile? Because it could be sweet or savory!",
    "What do you call a fish that's a firefighter? A hose-fish!",
    "Why don't scientists trust velcro? Because it's always sticking to things!",
    "What do you call a pig that's a cruise director? Captain Ham-ahoy!",
    "Why did the tamarind pucker up? Because it was having a sour moment!",
    "What do you call a fish that's a police officer? A cop-fish!",
    "Why don't scientists trust magnets on fridges? Because they're always attracting attention!",
    "What do you call a cow that's a wedding planner? A moo-nificent organizer!",
    "Why did the guava blush? Because it was feeling sweet on someone!",
    "What do you call a fish that's a banker? A loan-shark... wait, that's different!",
    "Why don't scientists trust sticky notes? Because they're always leaving reminders!",
    "What do you call a pig that's a tour guide? A ham-bassador of fun!",
    "Why did the custard apple feel creamy? Because it was having a smooth day!",
    "What do you call a fish that's a therapist? A counselor-fish!",
    "Why don't scientists trust tape? Because it's always sticking around!",
    "What do you call a cow that's a party planner? A moo-sic coordinator!",
    "Why did the sugar apple feel energetic? Because it was naturally sweet!",
    "What do you call a fish that's a personal trainer? A fit-ness fish!",
    "Why don't scientists trust glue? Because it's always bonding with things!",
    "What do you call a pig that's a DJ? DJ Ham-ster!",
    "Why did the ice cream apple feel cool? Because it was chilling out!",
    "What do you call a fish that's a chef? A cook-fish extraordinaire!",
    "Why don't scientists trust cement? Because it's always setting things in stone!",
    "What do you call a cow that's a event coordinator? A moo-ment maker!",
    "Why did the pond apple feel refreshing? Because it was making waves!",
    "What do you call a fish that's a artist? A paint-fish!",
    "Why don't scientists trust super glue? Because it's permanently attached to everything!",
    "What do you call a pig that's a motivational speaker? A ham-spiring leader!",
    "Why did the mountain apple feel elevated? Because it was on top of the world!",
    "What do you call a fish that's a writer? An author-fish!",
    "Why don't scientists trust duct tape? Because it fixes everything too well!",
    "What do you call a cow that's a fitness instructor? A moo-scle builder!",
    "Why did the rose apple smell so good? Because it was blooming with confidence!",
    "What do you call a fish that's a scientist? A research-fish!",
    "Why don't scientists trust double-sided tape? Because it's always two-faced!",
    "What do you call a pig that's a life coach? A ham-powerment specialist!",
    "Why did the wax apple shine so bright? Because it was polishing its skills!",
    "What do you call a fish that's a engineer? A technical-fish!",
    "Why don't scientists trust masking tape? Because it's always covering things up!",
    "What do you call a cow that's a dance instructor? A moo-vement teacher!",
    "Why did the java apple feel energized? Because it was brewing with excitement!",
    "What do you call a fish that's a pilot? A fly-fish!",
    "Why don't scientists trust packing tape? Because it's always sealing the deal!",
    "What do you call a pig that's a relationship counselor? A ham-mony expert!",
    "Why did the bell fruit ring so clearly? Because it had perfect pitch!",
    "What do you call a fish that's a astronaut? A space-fish!",
    "Why don't scientists trust electrical tape? Because it's always conducting business!",
    "What do you call a cow that's a meditation teacher? A moo-nful instructor!",
    "Why did the water apple feel hydrated? Because it was going with the flow!",
    "What do you call a fish that's a detective? Sherlock Fins!",
    "Why don't scientists trust painter's tape? Because it's always masking the truth!",
    "What do you call a pig that's a conflict resolution specialist? A ham-monious mediator!",
    "Why did the cloud apple feel light? Because it was floating on air!",
    "What do you call a fish that's a mathematician? A cal-cu-later fish!",
    "Why don't scientists trust medical tape? Because it's always patching things up!",
    "What do you call a cow that's a stress management coach? A moo-ditation expert!",
    "Why did the monkey apple swing into action? Because it was going bananas with joy!",
    "What do you call a fish that's a philosopher? A deep-thinking fish!",
    "Why don't scientists trust gorilla tape? Because it's the strongest bond of all!",
    "What do you call a pig that's a happiness consultant? A ham-ful joy spreader!",
    "Why did the elephant apple feel massive? Because it was thinking big!",
    "What do you call a fish that's a meteorologist? A weather-fish!",
    "Why don't scientists trust fashion tape? Because it's always holding outfits together!",
    "What do you call a cow that's a mindfulness teacher? A moo-ment of zen instructor!",
    "Why did the tiger apple feel fierce? Because it had the eye of the tiger!",
    "What do you call a fish that's a geologist? A rock-fish!",
    "Why don't scientists trust carpet tape? Because it's always laying down the law!",
    "What do you call a pig that's a positivity coach? A ham-mazing attitude adjuster!",
    "Why did the lion apple roar with pride? Because it was the king of fruits!",
    "What do you call a fish that's a archaeologist? A history-fish!",
    "Why don't scientists trust foam tape? Because it's always cushioning the blow!",
    "What do you call a cow that's a self-esteem coach? A moo-tivational confidence builder!",
    "Why did the bear apple hibernate? Because it was saving energy for spring!",
    "What do you call a fish that's a linguist? A poly-glot fish!",
    "Why don't scientists trust transfer tape? Because it's always moving things around!",
    "What do you call a pig that's a wellness coordinator? A ham-listic health helper!",
    "Why did the deer apple leap with joy? Because it was bounding with happiness!",
    "What do you call a fish that's a psychologist? A mind-fish!",
    "Why don't scientists trust mounting tape? Because it's always putting things up!",
    "What do you call a cow that's a leadership coach? A moo-nificent mentor!",
    "Why did the rabbit apple hop around? Because it was multiplying the fun!",
    "What do you call a fish that's a sociologist? A society-fish!",
    "Why don't scientists trust reflective tape? Because it's always showing the bright side!",
    "What do you call a pig that's a team building facilitator? A ham-unity creator!",
    "Why did the fox apple feel clever? Because it was outsmarting everyone!",
    "What do you call a fish that's a anthropologist? A culture-fish!",
    "Why don't scientists trust glow-in-the-dark tape? Because it's always lighting up the room!",
    "What do you call a cow that's a empowerment coach? A moo-jestic strength builder!",
    "Why did the wolf apple howl with delight? Because it was having a pack-tastic time!",
    "What do you call a fish that's a economist? A market-fish!",
    "Why don't scientists trust magnetic tape? Because it's always attracting success!",
    "What do you call a pig that's a innovation consultant? A ham-azing idea generator!",
    "I'm reading a book about anti-gravity. It's impossible to put down!",
    "I told my cat a joke about a ball of yarn. He was in stitches!",
    "The math teacher called in sick with algebra. Don't worry, it's just a logarithm!",
    "I used to be addicted to soap, but I'm clean now.",
    "The graveyard is so crowded, people are dying to get in!",
    "I'm terrified of elevators, so I'll take steps to avoid them.",
    "The shovel was a ground-breaking invention.",
    "I lost my job at the bank. A woman asked me to check her balance, so I pushed her over.",
    "I'm friends with 25 letters of the alphabet. I don't know Y.",
    "The early bird might get the worm, but the second mouse gets the cheese.",
    "I wondered why the baseball kept getting bigger. Then it hit me.",
    "A bicycle can't stand on its own because it's two-tired.",
    "I used to hate facial hair, but then it grew on me.",
    "The scarecrow won an award because he was outstanding in his field.",
    "I'm reading a book on the history of glue. Can't put it down!",
    "My wife said I should do lunges to stay in shape. That would be a big step forward.",
    "Why don't scientists trust atoms? Because they make up everything!",
    "I bought the world's worst thesaurus yesterday. Not only is it terrible, it's terrible.",
    "I haven't slept for ten days, because that would be too long.",
    "A photon checks into a hotel. The bellhop asks if he has any luggage. He says, 'No, I'm traveling light.'",
    "I'm writing a book about hurricanes and tornadoes. It's only a draft.",
    "The rotation of earth really makes my day.",
    "I was wondering why the frisbee kept getting bigger, then it hit me.",
    "My friend's bakery burned down last night. Now his business is toast.",
    "I stayed up all night wondering where the sun went. Then it dawned on me.",
    "The man who survived mustard gas and pepper spray is now a seasoned veteran.",
    "I'm addicted to brake fluid, but I can stop anytime.",
    "How do you organize a space party? You planet!",
    "I got a job crushing cans. It was soda pressing.",
    "What's the best thing about Switzerland? I don't know, but the flag is a big plus.",
    "I invented a new word: Plagiarism!",
    "Did you hear about the guy who got hit in the head with a can of soda? He was lucky it was a soft drink.",
    "I told my wife she was drawing her eyebrows too high. She looked surprised.",
    "Why don't skeletons fight each other? They don't have the guts.",
    "What do you call a fake noodle? An impasta!",
    "I would avoid the sushi if I were you. It's a little fishy.",
    "Want to hear a joke about paper? Never mind, it's tearable.",
    "Why did the coffee file a police report? It got mugged.",
    "I used to be a personal trainer. Then I gave my too weak notice.",
    "What's the difference between a poorly dressed man on a tricycle and a well-dressed man on a bicycle? Attire.",
    "I'm going to stand outside. So if anyone asks, I'm outstanding.",
    "Why don't eggs tell jokes? They'd crack each other up.",
    "Did you hear about the mathematician who's afraid of negative numbers? He'll stop at nothing to avoid them.",
    "I lost my job as a massage therapist. I rubbed people the wrong way.",
    "What do you call a bear with no teeth? A gummy bear!",
    "I'm thinking about removing my spine. It's holding me back.",
    "Why did the invisible man turn down the job offer? He couldn't see himself doing it.",
    "I used to work in a shoe recycling shop. It was sole destroying.",
    "What do you call a sleeping bull? A bulldozer!",
    "I'm reading a book about teleportation. It's bound to take me places.",
    "Why did the golfer bring two pairs of pants? In case he got a hole in one!",
    "I tried to catch some fog earlier. I mist.",
    "What do you call a dinosaur that crashes his car? Tyrannosaurus Wrecks!",
    "I'm studying to become a historian. There's no future in it, but there's a lot of past.",
    "Why don't scientists trust atoms? Because they make up everything!",
    "I told a chemistry joke, but there was no reaction.",
    "What's orange and sounds like a parrot? A carrot!",
    "I'm friends with a lot of vegetarians. Most of my friends are either veggie-tables or fungi to be around.",
    "Why did the bicycle fall over? It was two-tired!",
    "I'm learning sign language. It's pretty handy.",
    "What do you call a fish wearing a crown? A king fish!",
    "I used to be addicted to the hokey pokey, but I turned myself around.",
    "Why don't skeletons go to scary movies? They don't have the guts!",
    "What do you call a cow with no legs? Ground beef!",
    "I'm reading a book about mazes. I got lost in it.",
    "Why did the scarecrow win an award? He was outstanding in his field!",
    "What do you call a belt made of watches? A waist of time!",
    "I'm writing my autobiography. It's a work of friction.",
    "Why don't eggs tell each other jokes? Because they'd crack up!",
    "What do you call a sleeping bull? A bulldozer!",
    "I told my wife she should embrace her mistakes. She gave me a hug.",
    "Why did the math book look so sad? Because it had too many problems!",
    "What do you call a bear in the rain? A drizzly bear!",
    "I'm on a seafood diet. I see food and eat it.",
    "Why don't scientists trust stairs? Because they're always up to something!",
    "What do you call a pig that does karate? A pork chop!",
    "I used to hate facial hair, but then it grew on me.",
    "Why did the coffee go to the police? It got mugged!",
    "What do you call a fake noodle? An impasta!",
    "I'm reading a book on anti-gravity. It's impossible to put down!",
    "Why don't skeletons fight each other? They don't have the guts!",
    "What do you call a fish with two knees? A two-knee fish!",
    "I told a joke about unemployed people, but none of them worked.",
    "Why did the banana go to the doctor? It wasn't peeling well!",
    "What do you call a cow that can play a musical instrument? A moo-sician!",
    "I'm friends with all the planets except one. I have no space for Uranus.",
    "Why don't eggs go to comedy shows? They might crack up!",
    "What do you call a dinosaur that loves to sleep? A dino-snore!",
    "I tried to write a joke about time travel, but you didn't like it.",
    "Why did the cookie go to the doctor? Because it felt crumbly!",
    "What do you call a sheep with no legs? A cloud!",
    "I'm writing a book about hurricanes. It's only a draft.",
    "Why don't scientists trust atoms? They make up everything!",
    "What do you call a bear with no ears? B!",
    "I told my computer a joke, but it didn't get it. It must have been a hard drive.",
    "Why did the tomato turn red? Because it saw the salad dressing!",
    "What do you call a cow in an earthquake? A milkshake!",
    "I'm addicted to collecting vintage synthesizers. I have a Roland addiction.",
    "Why don't skeletons go to barbecues? They don't have the stomach for it!",
    "What do you call a fish that needs help with vocals? Auto-tuna!",
    "I told a joke about a broken pencil, but it was pointless.",
    "Why did the orange stop rolling down the hill? It ran out of juice!",
    "What do you call a pig that's been arrested? A ham in cuffs!",
    "I'm reading a book about submarines. It's deep.",
]


def is_informative(title):
    if not title:
        return False
    title_clean = title.strip().lower()
    if len(title_clean.split()) < 4:
        return False
    for pattern in CLICKBAIT_PATTERNS:
        if re.search(pattern, title_clean):
            return False
    return True


def fetch_rss_feed(name, url, limit=10):
    try:
        response = httpx.get(url, timeout=10)
        response.raise_for_status()
        root = ET.fromstring(response.text)

        items = []
        for item in root.findall("./channel/item")[:limit]:  # take only top N
            title = item.findtext("title")
            description = item.findtext("description") or ""
            pub_date = item.findtext("pubDate")

            if is_informative(title):
                items.append(
                    {
                        "source": name,
                        "title": title.strip(),
                        "link": item.findtext("link"),
                        "description": description.strip(),
                        "pubDate": pub_date,
                    },
                )
        return items
    except Exception as e:
        logger.error(f"Error fetching RSS feed {name} from {url}: {e}")
        return []


def fetch_all_news(limit_per_feed=10):
    all_items = []
    for name, url in FEEDS.items():
        all_items.extend(fetch_rss_feed(name, url, limit=limit_per_feed))
    return all_items


class NewsComplimentsFeed(BaseComponent):
    def __init__(self, *args, limit_per_feed=10, **kwargs):
        super().__init__(name="news_compliments", *args, **kwargs)
        self.limit_per_feed = limit_per_feed

    def summary_layout(self):
        return html.Div(
            [
                dcc.Interval(
                    id=f"{self.component_id}-interval-fetch",
                    interval=600_000,  # 10 minutes
                ),
                dcc.Interval(
                    id=f"{self.component_id}-interval-display",
                    interval=8_000,  # 8 seconds for display rotation
                ),
                dcc.Store(
                    id=f"{self.component_id}-store",
                    data=None,
                ),
                dcc.Store(
                    id=f"{self.component_id}-display-idx",
                    data=0,
                ),
                html.Div(
                    id=f"{self.component_id}-display",
                    style={
                        "display": "flex",
                        "flexDirection": "column",
                        "alignItems": "stretch",
                        "gap": "8px",
                        "width": "100%",
                        "color": COLORS["white"],
                        "fontFamily": FONT_FAMILY,
                    },
                ),
            ],
        )

    @cache_json(valid_lifetime=datetime.timedelta(minutes=15))
    def fetch(self):
        try:
            return fetch_all_news(limit_per_feed=self.limit_per_feed)
        except Exception as e:
            logger.error(f"Error fetching news: {e}")
            return []

    def add_callbacks(self, app):
        @app.callback(
            Output(f"{self.component_id}-store", "data"),
            Input(f"{self.component_id}-interval-fetch", "n_intervals"),
        )
        def fetch_data(n_intervals):
            return self.fetch()

        # Update the display index every 8 seconds
        @app.callback(
            Output(f"{self.component_id}-display-idx", "data"),
            Input(f"{self.component_id}-interval-display", "n_intervals"),
            Input(f"{self.component_id}-store", "data"),
            prevent_initial_call=True,
        )
        def update_display_idx(n_intervals, data):
            # Always return a new random value to trigger display update
            return random.randint(0, 10000)  # Large range to ensure uniqueness

        # Show either news or compliment/joke with 50-50 chance
        app.clientside_callback(
            f"""
            function(news_data, idx) {{
                const container = document.getElementById('{self.component_id}-display');
                if (!container) return window.dash_clientside.no_update;
                container.innerHTML = '';
                
                // 50-50 chance between news and compliment/joke
                const showNews = Math.random() < 0.5;
                
                if (showNews && news_data && Array.isArray(news_data) && news_data.length > 0) {{
                    // Show random news item
                    const randomIdx = Math.floor(Math.random() * news_data.length);
                    const item = news_data[randomIdx];
                    
                    const newsCard = document.createElement('div');
                    newsCard.style.cssText = `
                        background: linear-gradient(135deg, rgba(255,255,255,0.06), rgba(255,255,255,0.02));
                        border: 1px solid rgba(255,255,255,0.08);
                        borderRadius: 8px;
                        padding: 12px 14px;
                        marginBottom: 0;
                        backdropFilter: blur(10px);
                        display: flex;
                        alignItems: center;
                        justifyContent: space-between;
                        width: 100%;
                        gap: 8px;
                    `;
                    
                    // Left side: news title
                    const leftDiv = document.createElement('div');
                    leftDiv.style.cssText = `
                        display: flex;
                        alignItems: center;
                        overflow: hidden;
                        flex: 1;
                    `;
                    
                    const title = document.createElement('span');
                    title.textContent = item.title || 'No Title';
                    title.style.cssText = `
                        fontWeight: 500;
                        fontSize: 1.1rem;
                        color: #FFFFFF;
                        overflow: hidden;
                        textOverflow: ellipsis;
                        whiteSpace: nowrap;
                        lineHeight: 1.2;
                        flex: 1;
                    `;
                    
                    leftDiv.appendChild(title);
                    
                    // Right side: source
                    const rightDiv = document.createElement('div');
                    rightDiv.style.cssText = `
                        display: flex;
                        alignItems: center;
                        whiteSpace: nowrap;
                        textAlign: right;
                    `;
                    
                    if (item.source) {{
                        const source = document.createElement('span');
                        source.textContent = item.source;
                        source.style.cssText = `
                            fontSize: 1rem;
                            color: #FFA500;
                            fontWeight: 500;
                        `;
                        rightDiv.appendChild(source);
                    }}
                    
                    newsCard.appendChild(leftDiv);
                    newsCard.appendChild(rightDiv);
                    container.appendChild(newsCard);
                    
                }} else {{
                    // Show random compliment or joke
                    const compliments = {COMPLIMENTS};
                    const jokes = {JOKES};
                    
                    // Combine all content
                    const allContent = [...compliments, ...jokes];
                    const randomIdx = Math.floor(Math.random() * allContent.length);
                    const content = allContent[randomIdx];
                    
                    const contentCard = document.createElement('div');
                    contentCard.style.cssText = `
                        background: linear-gradient(135deg, rgba(255,255,255,0.06), rgba(255,255,255,0.02));
                        border: 1px solid rgba(255,255,255,0.08);
                        borderRadius: 8px;
                        padding: 12px 14px;
                        marginBottom: 0;
                        backdropFilter: blur(10px);
                        display: flex;
                        alignItems: center;
                        justifyContent: center;
                        width: 100%;
                        textAlign: center;
                    `;
                    
                    // Centered content
                    const text = document.createElement('span');
                    text.textContent = content;
                    text.style.cssText = `
                        fontWeight: 500;
                        fontSize: 1.1rem;
                        color: #FFFFFF;
                        lineHeight: 1.2;
                        textAlign: center;
                    `;
                    
                    contentCard.appendChild(text);
                    container.appendChild(contentCard);
                }}
                
                return window.dash_clientside.no_update;
            }}
            """,
            Output(f"{self.component_id}-display", "children"),
            Input(f"{self.component_id}-store", "data"),
            Input(f"{self.component_id}-display-idx", "data"),
            prevent_initial_call=True,
        )
