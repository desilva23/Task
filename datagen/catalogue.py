"""The curated demo catalogue: what sits in which aisle, and the scenario anchors.

Names, categories and positions are fixed here; the seed draws only the details (build.py).
An item line reads ``name | brand | size | synonyms | overrides``; ``OB`` means Own Brand.
Overrides are ``key=value`` pairs and always win over the seed:

    sku, price, pop, stock, rack, shelf, facings   fixed values
    gf, vegan, veg, halal                          t, f, or empty for unknown
    allergens                                      a|list, none, or empty for unknown
    age                                            t or f
    ranged=f                                       not carried here: no stock, no placement
    unplaced                                       ranged and stocked but no placement (EC-19)
    endcap=N|S                                     a fixed promotional end cap on its own aisle

Anchors used by later acceptance tests are marked with the AC or EC they serve.
"""

from dataclasses import dataclass

# (gluten free, vegan, vegetarian, halal, allergens) as CSV tokens; "" is unknown.
DIET = {
    "plant": ("true", "true", "true", "true", "none"),
    "bread": ("false", "true", "true", "true", "gluten"),
    "dairy": ("true", "false", "true", "true", "milk"),
    "meat": ("true", "false", "false", "", "none"),
    "ready": ("false", "false", "false", "", "gluten|milk"),
    "veggie": ("false", "false", "true", "", "gluten|milk"),
    "cereal": ("false", "true", "true", "true", "gluten"),
    "drink": ("true", "true", "true", "", "none"),
    "snack": ("false", "true", "true", "true", "none"),
    "sweet": ("true", "false", "true", "", "milk"),
    "beer": ("false", "", "", "false", "gluten"),
    "wine": ("true", "", "", "false", "sulphites"),
    "spirit": ("true", "", "", "false", "none"),
    "fish": ("true", "false", "false", "", "fish"),
    "nonfood": ("", "", "", "", ""),
}


@dataclass(frozen=True)
class Aisle:
    level: int
    number: int
    department: str
    category: str
    placement: str  # HOME, CHILLER or SEASONAL — the location type of its racks
    diet: str
    price: tuple[float, float]
    items: str
    age_restricted: bool = False

    @property
    def shelf_count(self) -> int:
        return {"CHILLER": 4, "SEASONAL": 3}.get(self.placement, 5)


@dataclass(frozen=True)
class Spot:
    """A counter or locked cabinet and the products sold only there."""

    node_id: str
    location_type: str  # COUNTER or ASSISTED
    department: str
    category: str
    diet: str
    price: tuple[float, float]
    items: str
    age_restricted: bool = False


AISLES = (
    # ── Ground floor: Fresh Food ────────────────────────────────────────────────
    Aisle(
        0,
        1,
        "Fruit & Veg",
        "Fruit",
        "HOME",
        "plant",
        (0.6, 3.5),
        """
        Bananas | OB | 5 pack | banana
        Gala Apples | OB | 6 pack | apple|apples
        Strawberries | OB | 400g | strawberry
        Blueberries | OB | 150g | blueberry
        Easy Peeler Clementines | OB | 600g | clementine|satsuma|orange
    """,
    ),
    Aisle(
        0,
        2,
        "Fruit & Veg",
        "Vegetables",
        "HOME",
        "plant",
        (0.5, 2.5),
        """
        Carrots | OB | 1kg | carrot
        Broccoli | OB | 350g | brocoli
        Baking Potatoes | OB | 4 pack | potato|potatoes|spuds
        Brown Onions | OB | 1kg | onion
        Salad Tomatoes | OB | 6 pack | tomato|tomatoes
        Organic Kale | OB | 200g | kale | ranged=f
    """,
    ),
    Aisle(
        0,
        3,
        "Bakery",
        "Bread",
        "HOME",
        "bread",
        (0.9, 2.2),
        """
        White Bread Medium Sliced | OB | 800g | bread|white bread|loaf
        Wholemeal Bread Medium Sliced | OB | 800g | bread|brown bread|loaf
        Seeded Batch Loaf | OB | 800g | bread|loaf | allergens=gluten|sesame
        Gluten Free White Bread | Free From | 400g | bread|gf bread | gf=t vegan=f allergens=eggs stock=0
    """,
    ),  # AC-17: sold out, and no gluten-free alternative in its category
    Aisle(
        0,
        4,
        "Bakery",
        "Rolls & Wraps",
        "HOME",
        "bread",
        (0.8, 2.0),
        """
        Soft White Rolls | OB | 6 pack | rolls|baps
        Plain Tortilla Wraps | OB | 8 pack | wraps|tortilla
        Crumpets | OB | 6 pack | crumpet
        English Muffins | OB | 4 pack | muffins
    """,
    ),
    Aisle(
        0,
        5,
        "Dairy",
        "Milk",
        "CHILLER",
        "dairy",
        (0.9, 1.9),
        """
        Semi Skimmed Milk | OB | 2 pint | milk|semi skimmed
        Whole Milk | OB | 2 pint | milk|full fat
        Skimmed Milk | OB | 2 pint | milk|skimmed
        Semi Skimmed Milk | OB | 4 pint | milk|semi skimmed
        Oat Drink | Oatly | 1l | oat milk|milk alternative | gf=f vegan=t allergens=gluten
    """,
    ),  # AC-02, AC-03: "milk" matches several products
    Aisle(
        0,
        6,
        "Dairy",
        "Cheese & Butter",
        "CHILLER",
        "dairy",
        (1.0, 4.5),
        """
        Mature Cheddar | OB | 400g | cheese|cheddar
        Mozzarella | OB | 125g | cheese
        Salted Butter | OB | 250g | butter
        Spreadable Butter | Lurpak | 500g | butter|spread
        Halloumi | OB | 225g | cheese
    """,
    ),
    Aisle(
        0,
        7,
        "Dairy",
        "Eggs & Yogurt",
        "CHILLER",
        "dairy",
        (0.8, 3.5),
        """
        Free Range Eggs | OB | 6 pack | eggs|egg | vegan=f allergens=eggs
        Free Range Eggs | OB | 12 pack | eggs|egg | vegan=f allergens=eggs
        Large Free Range Eggs | Happy Egg | 6 pack | eggs|egg | vegan=f allergens=eggs
        Natural Yogurt | OB | 500g | yogurt|yoghurt
        Strawberry Yogurt | Muller | 4 x 125g | yogurt|yoghurt
    """,
    ),
    Aisle(
        0,
        8,
        "Meat & Fish",
        "Fresh Meat",
        "CHILLER",
        "meat",
        (2.0, 6.5),
        """
        Chicken Breast Fillets | OB | 600g | chicken
        Beef Mince 5% Fat | OB | 500g | mince|beef
        Pork Sausages | OB | 8 pack | sausages|bangers | gf=f halal=f allergens=gluten|sulphites
        Smoked Back Bacon | OB | 300g | bacon | halal=f
        Halal Chicken Thighs | OB | 1kg | chicken|halal | halal=t
    """,
    ),
    Aisle(
        0,
        9,
        "Chilled",
        "Ready Meals",
        "CHILLER",
        "ready",
        (2.5, 4.5),
        """
        Beef Lasagne | OB | 400g | lasagne|lasagna
        Chicken Tikka Masala | OB | 400g | curry|tikka
        Macaroni Cheese | OB | 400g | mac and cheese | veg=t
        Cottage Pie | OB | 400g | pie
    """,
    ),
    Aisle(
        0,
        10,
        "Chilled",
        "Pizza & Dips",
        "CHILLER",
        "veggie",
        (1.0, 4.0),
        """
        Margherita Pizza | OB | 12 inch | pizza
        Pepperoni Pizza | OB | 12 inch | pizza | veg=f halal=f
        Houmous | OB | 200g | hummus|houmous | gf=t vegan=t halal=t allergens=sesame
        Fresh Guacamole | OB | 150g | guac|guacamole | gf=t vegan=t halal=t allergens=none
    """,
    ),
    Aisle(
        0,
        11,
        "Frozen",
        "Frozen Veg & Chips",
        "CHILLER",
        "plant",
        (1.0, 3.0),
        """
        Garden Peas | OB | 900g | peas|frozen peas
        Oven Chips | McCain | 1.5kg | chips|fries
        Sweetcorn | OB | 750g | corn
        Mixed Vegetables | OB | 1kg | frozen veg
    """,
    ),
    Aisle(
        0,
        12,
        "Frozen",
        "Ice Cream & Desserts",
        "CHILLER",
        "sweet",
        (1.5, 5.0),
        """
        Vanilla Ice Cream | OB | 1l | ice cream
        Chocolate Ice Cream | Ben & Jerry's | 465ml | ice cream
        Fruit Ice Lollies | OB | 6 pack | lolly|lollies | vegan=t allergens=none
        Lemon Cheesecake | OB | 450g | cheesecake|dessert | gf=f allergens=gluten|milk|eggs
    """,
    ),
    # ── First floor: Food Cupboard & Drinks ─────────────────────────────────────
    Aisle(
        1,
        1,
        "Food Cupboard",
        "Breakfast Cereals",
        "HOME",
        "cereal",
        (1.0, 4.0),
        """
        Corn Flakes | Kellogg's | 500g | cornflakes|cereal
        Porridge Oats | OB | 1kg | oats|porridge
        Bran Flakes | OB | 750g | cereal
        Crunchy Granola | OB | 500g | granola|cereal | allergens=gluten|nuts
        Rice Pops | OB | 440g | cereal | gf=f
    """,
    ),
    Aisle(
        1,
        2,
        "Food Cupboard",
        "Tea & Coffee",
        "HOME",
        "plant",
        (1.5, 6.0),
        """
        Everyday Tea Bags | OB | 80 pack | tea|teabags
        Instant Coffee | Nescafe | 200g | coffee
        Ground Coffee | OB | 227g | coffee
        Green Tea | Twinings | 40 pack | tea
    """,
    ),
    Aisle(
        1,
        3,
        "Food Cupboard",
        "Tins & Cans",
        "HOME",
        "plant",
        (0.5, 2.0),
        """
        Baked Beans | Heinz | 415g | beans|baked beans
        Chopped Tomatoes | OB | 400g | tinned tomatoes|tomatoes
        Tuna Chunks in Spring Water | OB | 145g | tuna|fish | vegan=f veg=f allergens=fish
        Cream of Tomato Soup | Heinz | 400g | soup | vegan=f allergens=milk
        Chickpeas | OB | 400g | chickpea
    """,
    ),
    Aisle(
        1,
        4,
        "Food Cupboard",
        "Pasta, Rice & Noodles",
        "HOME",
        "cereal",
        (0.8, 3.0),
        """
        Fusilli | OB | 500g | pasta
        Spaghetti | OB | 500g | pasta
        Basmati Rice | Tilda | 1kg | rice | gf=t allergens=none
        Egg Noodles | OB | 250g | noodles | vegan=f allergens=gluten|eggs
        Gluten Free Penne | Free From | 500g | pasta|gf pasta | gf=t allergens=none
    """,
    ),
    Aisle(
        1,
        5,
        "Food Cupboard",
        "Cooking Sauces",
        "HOME",
        "plant",
        (1.0, 3.0),
        """
        Tomato & Basil Pasta Sauce | Dolmio | 500g | pasta sauce
        Tikka Masala Sauce | Patak's | 450g | curry sauce | vegan=f allergens=milk
        Green Pesto | OB | 190g | pesto | vegan=f halal= allergens=milk|nuts
        Sweet & Sour Sauce | OB | 500g | sauce
    """,
    ),
    Aisle(
        1,
        6,
        "Food Cupboard",
        "Condiments & Oils",
        "HOME",
        "plant",
        (0.6, 5.0),
        """
        Tomato Ketchup | Heinz | 460g | ketchup|tomato sauce
        Mayonnaise | Hellmann's | 400g | mayo | vegan=f allergens=eggs
        Extra Virgin Olive Oil | OB | 500ml | olive oil|oil
        Vegetable Oil | OB | 1l | oil
        Table Salt | OB | 750g | salt
    """,
    ),
    Aisle(
        1,
        7,
        "Drinks",
        "Soft Drinks",
        "HOME",
        "drink",
        (0.9, 2.5),
        """
        Coca-Cola Classic | Coca-Cola | 500ml | coke|cola|coca cola | sku=7123456 price=1.65 pop=0.82 stock=14 rack=3 shelf=2 facings=3 endcap=N
        Diet Coke | Coca-Cola | 500ml | coke|cola|diet coke | stock=0
        Coca-Cola Zero Sugar | Coca-Cola | 500ml | coke|cola|coke zero | stock=22
        Cloudy Lemonade | OB | 2l | lemonade
        Orange Squash | Robinsons | 1l | squash|cordial
        Pepsi Max Cola | Pepsi | 500ml | pepsi|cola|pepsi max cola | ranged=f
    """,
    ),  # AC-01, AC-21 (Coca-Cola, two placements); AC-17, AC-20 (Diet Coke); AC-19, AC-20 (Pepsi)
    Aisle(
        1,
        8,
        "Drinks",
        "Water & Juice",
        "HOME",
        "drink",
        (0.5, 3.0),
        """
        Still Spring Water | OB | 6 x 500ml | water
        Sparkling Water | OB | 2l | fizzy water|water
        Smooth Orange Juice | Tropicana | 1l | orange juice|oj|juice
        Apple Juice | OB | 1l | juice
        Sparkling Water Lime | OB | 1l | fizzy water|water | unplaced
        Kombucha Ginger | Remedy | 330ml | kombucha | ranged=f
    """,
    ),  # EC-19: Sparkling Water Lime is ranged and stocked with no recorded shelf
    Aisle(
        1,
        9,
        "Food Cupboard",
        "Crisps & Snacks",
        "HOME",
        "snack",
        (0.8, 3.0),
        """
        Ready Salted Crisps | Walkers | 6 pack | crisps
        Salt & Vinegar Crisps | Walkers | 6 pack | crisps
        Sea Salt Kettle Chips | Kettle | 150g | crisps
        Salted Peanuts | OB | 200g | peanuts|nuts | gf=t allergens=peanuts
        Lightly Salted Tortilla Chips | OB | 200g | nachos|tortilla chips
    """,
    ),
    Aisle(
        1,
        10,
        "Food Cupboard",
        "Biscuits",
        "HOME",
        "veggie",
        (0.6, 2.5),
        """
        Digestive Biscuits | McVitie's | 400g | digestives|biscuits
        Milk Chocolate Digestives | McVitie's | 300g | biscuits|chocolate biscuits
        Rich Tea | OB | 300g | biscuits
        Custard Creams | OB | 400g | biscuits
    """,
    ),
    Aisle(
        1,
        11,
        "Food Cupboard",
        "Chocolate & Sweets",
        "HOME",
        "sweet",
        (0.7, 3.0),
        """
        Milk Chocolate Bar | Cadbury | 110g | chocolate
        Dark Chocolate 70% | OB | 100g | chocolate | vegan=t allergens=none
        Fruit Pastilles | Rowntree's | 143g | sweets | veg=f allergens=none
        Mint Imperials | OB | 200g | mints|sweets | vegan=t allergens=none
    """,
    ),
    Aisle(
        1,
        12,
        "Food Cupboard",
        "Home Baking",
        "HOME",
        "plant",
        (0.8, 3.5),
        """
        Plain Flour | OB | 1.5kg | flour | gf=f allergens=gluten
        Self Raising Flour | OB | 1.5kg | flour | gf=f allergens=gluten
        Caster Sugar | Silver Spoon | 1kg | sugar
        Baking Powder | OB | 170g | baking
        Vanilla Extract | Nielsen-Massey | 60ml | vanilla
    """,
    ),
    Aisle(
        1,
        13,
        "Beer, Wine & Spirits",
        "Beer & Cider",
        "HOME",
        "beer",
        (3.0, 7.0),
        """
        Premium Lager | OB | 4 x 440ml | beer|lager
        Pale Ale | OB | 500ml | beer|ipa
        Apple Cider | OB | 4 x 500ml | cider | gf=t allergens=sulphites
        Alcohol Free Lager | OB | 4 x 330ml | beer|alcohol free|lager | age=f
    """,
        age_restricted=True,
    ),
    Aisle(
        1,
        14,
        "Beer, Wine & Spirits",
        "Wine",
        "HOME",
        "wine",
        (5.0, 12.0),
        """
        Sauvignon Blanc | OB | 75cl | wine|white wine
        Merlot | OB | 75cl | wine|red wine
        Prosecco | OB | 75cl | fizz|sparkling wine
        Provence Rose | OB | 75cl | wine|rose wine
    """,
        age_restricted=True,
    ),
    # ── Second floor: Home, Health & Baby ───────────────────────────────────────
    Aisle(
        2,
        1,
        "Health & Beauty",
        "Hair & Body",
        "HOME",
        "nonfood",
        (1.0, 5.0),
        """
        Everyday Shampoo | OB | 400ml | shampoo
        Everyday Conditioner | OB | 400ml | conditioner
        Shower Gel | Radox | 250ml | body wash
        Roll On Deodorant | Sure | 50ml | deodorant|deo
        Antibacterial Hand Wash | Carex | 250ml | soap|hand soap
    """,
    ),
    Aisle(
        2,
        2,
        "Health & Beauty",
        "Oral Care",
        "HOME",
        "nonfood",
        (1.0, 4.5),
        """
        Fluoride Toothpaste | Colgate | 75ml | toothpaste
        Medium Toothbrush | OB | 2 pack | toothbrush
        Mouthwash | Listerine | 500ml | mouthwash
        Dental Floss | OB | 50m | floss
    """,
    ),
    Aisle(
        2,
        3,
        "Health & Beauty",
        "Medicines",
        "HOME",
        "nonfood",
        (0.5, 5.0),
        """
        Paracetamol 500mg | OB | 16 tablets | paracetamol|painkillers
        Ibuprofen 200mg | OB | 16 tablets | ibuprofen|painkillers
        Fabric Plasters | Elastoplast | 40 pack | plasters|band aid
        Cold & Flu Capsules | Lemsip | 16 pack | cold|flu
        Antiseptic Cream | Savlon | 30g | antiseptic
    """,
    ),
    Aisle(
        2,
        4,
        "Household",
        "Cleaning",
        "HOME",
        "nonfood",
        (0.8, 6.0),
        """
        Washing Up Liquid | Fairy | 433ml | washing up|dish soap
        Multi Surface Spray | Dettol | 750ml | cleaner|spray
        Thick Bleach | OB | 750ml | bleach
        Dishwasher Tablets | Finish | 30 pack | dishwasher
        Sponge Scourers | OB | 4 pack | sponges|scourer
    """,
    ),
    Aisle(
        2,
        5,
        "Household",
        "Laundry",
        "HOME",
        "nonfood",
        (2.0, 8.0),
        """
        Bio Laundry Liquid | Persil | 1.3l | washing liquid|detergent
        Non Bio Washing Powder | OB | 1.4kg | washing powder|detergent
        Fabric Conditioner | Comfort | 1.3l | softener
        Stain Remover | Vanish | 1l | stain
    """,
    ),
    Aisle(
        2,
        6,
        "Household",
        "Kitchen Roll & Toilet Tissue",
        "HOME",
        "nonfood",
        (1.0, 6.0),
        """
        Toilet Tissue | Andrex | 9 roll | toilet roll|loo roll
        Kitchen Roll | Plenty | 2 pack | kitchen towel
        Facial Tissues | Kleenex | 3 pack | tissues
        Swing Bin Liners | OB | 20 pack | bin bags|bin liners
    """,
    ),
    Aisle(
        2,
        7,
        "Pet",
        "Pet Food & Care",
        "HOME",
        "nonfood",
        (1.5, 9.0),
        """
        Dry Dog Food | Bakers | 2kg | dog food
        Cat Food Pouches | Felix | 12 pack | cat food
        Clumping Cat Litter | OB | 10l | cat litter
        Dog Treats | Dentastix | 7 pack | dog treats
    """,
    ),
    Aisle(
        2,
        8,
        "Baby",
        "Baby Care",
        "HOME",
        "nonfood",
        (1.0, 9.0),
        """
        Nappies Size 4 | Pampers | 44 pack | nappies|diapers
        Baby Wipes | OB | 3 x 64 | wipes
        Baby Rice | Cow & Gate | 100g | baby food | gf=t vegan=t veg=t halal=t allergens=none
        Apple & Banana Puree | Ella's Kitchen | 4 x 100g | baby food | gf=t vegan=t veg=t halal=t allergens=none
    """,
    ),
    Aisle(
        2,
        9,
        "Household",
        "Home & Kitchen",
        "HOME",
        "nonfood",
        (1.0, 4.0),
        """
        Kitchen Foil | Bacofoil | 30m | foil
        Cling Film | OB | 30m | clingfilm
        Food Bags | OB | 50 pack | freezer bags
        Baking Paper | OB | 10m | parchment
    """,
    ),
    Aisle(
        2,
        10,
        "Seasonal",
        "Halloween",
        "SEASONAL",
        "nonfood",
        (1.0, 6.0),
        """
        Pumpkin Carving Kit | OB | 5 piece | pumpkin
        Halloween Sweets Tub | OB | 600g | sweets|halloween | gf=t vegan=f veg=f allergens=none
        Witch Hat | OB | each | fancy dress|costume
        Glow Sticks | OB | 15 pack | glow
        Trick or Treat Bucket | OB | each | halloween|bucket | stock=0
    """,
    ),  # EC-24: a sold-out seasonal product
)

SPOTS = (
    Spot(
        "F0-CTR-01",
        "COUNTER",
        "Deli",
        "Deli Counter",
        "meat",
        (1.2, 4.0),
        """
        Honey Roast Ham | OB | per 100g | ham | halal=f
        Mixed Olives | OB | per 100g | olives | vegan=t veg=t halal=t
        Large Pork Pie | OB | each | pork pie | gf=f halal=f allergens=gluten|eggs
    """,
    ),
    Spot(
        "F0-CTR-02",
        "COUNTER",
        "Meat & Fish",
        "Fish Counter",
        "fish",
        (1.5, 3.5),
        """
        Salmon Fillet | OB | per 100g | salmon|fish
        Cod Loin | OB | per 100g | cod|fish
        King Prawns | OB | per 100g | prawns|shrimp | allergens=crustaceans
    """,
    ),
    Spot(
        "F0-CTR-03",
        "COUNTER",
        "Bakery",
        "Bakery Counter",
        "veggie",
        (0.6, 3.0),
        """
        All Butter Croissant | OB | each | croissant | allergens=gluten|milk|eggs
        Sourdough Loaf | OB | each | sourdough|bread | vegan=t halal=t allergens=gluten
        Cinnamon Swirl | OB | each | cinnamon bun | allergens=gluten|milk|eggs
    """,
    ),  # AC-16: counter products — no shelf, colleague required
    Spot(
        "F1-CAB-01",
        "ASSISTED",
        "Beer, Wine & Spirits",
        "Spirits",
        "spirit",
        (14.0, 28.0),
        """
        London Dry Gin | Gordon's | 70cl | gin
        Vodka | Smirnoff | 70cl | vodka
        Blended Scotch Whisky | Famous Grouse | 70cl | whisky|whiskey
    """,
        age_restricted=True,
    ),  # AC-16: locked cabinet
    Spot(
        "F2-CAB-01",
        "ASSISTED",
        "Baby",
        "Baby Milk",
        "dairy",
        (9.0, 14.0),
        """
        First Infant Milk | Aptamil | 800g | formula|baby milk
        Follow On Milk | Aptamil | 800g | formula|baby milk
        Hungry Infant Milk | Cow & Gate | 800g | formula|baby milk
    """,
    ),
)

# Fixed dump-bin placements: (product name, size, bin node)
DUMP_BINS = (
    ("Strawberries", "400g", "F0-BIN-01"),
    ("Sea Salt Kettle Chips", "150g", "F1-BIN-01"),
)
PROMO_ENDCAPS = 20  # including the fixed Coca-Cola end cap


def parse_items(block: str) -> list[dict]:
    """Each line → {name, brand, size, synonyms, overrides}."""
    out = []
    for line in block.strip().splitlines():
        parts = [p.strip() for p in line.split(" | ")]
        name, brand, size, synonyms = parts[:4]
        overrides: dict[str, str] = {}
        for token in (parts[4] if len(parts) > 4 else "").split():
            key, _, value = token.partition("=")
            overrides[key] = value if "=" in token else "t"
        out.append(
            {
                "name": name,
                "brand": "Own Brand" if brand == "OB" else brand,
                "size": size,
                "synonyms": synonyms,
                "overrides": overrides,
            }
        )
    return out
