# Génère menu/menu.json à partir de la carte Agha (captures Scribd, mai 2024).
# Lancer : python3 tools/build_menu.py
import json, re, unicodedata, os

def slug(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")

# ---------- ingrédient -> pièce 3D ----------
SAUCES = {"creme d'ail": "#f7f3ea", "sauce tahine": "#d9c39a", "mayonnaise": "#f6edc8", "tartare": "#efe8d0",
          "sauce cocktail": "#f0a07a", "ketchup": "#b8261a", "sauce barbecue": "#5a2410", "sauce d'avocat": "#9cc25a",
          "sauce de poisson pimente": "#c0392b", "salade mayonnaise": "#f2e6c0", "hummus": "#e3cc9a"}
PROT = {"poulet": "#c98a3c", "blanc de poulet": "#c98a3c", "escalope": "#d9a04a", "foie": "#5a2614", "viande": "#6b3a1e",
        "roti": "#8a4a2a", "steak": "#5a2a12", "langue": "#b9806a", "cervelle": "#e3c3ae", "mortadelle": "#eaa9a3",
        "poisson": "#e8c27a", "filet de poisson": "#efd29a", "poisson pane": "#d9a04a", "kashkaval": "#f2dc8c",
        "dinde": "#e8c3a8", "shawarma": "#8a4a2a"}
SAUS = {"makanek": "#7a3418", "sojok": "#8f2a18", "hot dog": "#c46a3a", "saucisses": "#c46a3a", "kafta": "#6b3a1e"}

def part_for(name, kit):
    n = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().lower().strip()
    n = n.replace("creme d'ail", "creme d'ail")
    if n in SAUCES or n.startswith("sauce"):
        return "ramekin", {"color": SAUCES.get(n, "#e9d9b0")}
    if n in SAUS: return "sausage", {"color": SAUS[n]}
    if n in PROT:
        if kit in ("pizza", "manakish"): return "strips", {"color": PROT[n], "n": 14, "spread": 0.62}
        return "strips", {"color": PROT[n]}
    table = [
        ("crevettes", "shrimp", {}), ("calamars", "rings", {}), ("crabe", "dice", {"color": "#f2c4b5", "size": 0.05}),
        ("falafel", "falafel", {}), ("tomate", "dice", {"color": "#d63a2a"}), ("cornichon", "pickles", {}),
        ("salade de choux", "coleslaw", {}), ("laitue", "lettuce", {}), ("biwaz", "lettuce", {}), ("salade", "lettuce", {}),
        ("mais", "dice", {"color": "#f4c430", "size": 0.03}), ("mozzarella", "cheese", {}), ("fromage", "cheese", {}),
        ("roquefort", "cheese", {"color": "#e9e4cf"}), ("chevre", "cheese", {"color": "#f7f4ea"}), ("fondel", "cheese", {}),
        ("oignon", "onion", {}), ("poivron", "pepper", {}), ("champignon", "mushrooms", {}), ("olive", "olives", {}),
        ("concombre", "slices", {}), ("radis", "slices", {"r": 0.045, "skin": "#c2325a", "flesh": "#fbeef0"}),
        ("menthe", "flecks", {"color": "#3f8f2f", "n": 18, "spread": 0.2}), ("frites", "fries", {}),
        ("pommes de terre", "potato", {}), ("feuilles de vigne", "dolma", {}), ("chicoree", "greens", {}),
        ("labneh", "dollop", {"color": "#fbf7ee"}), ("citron", "lemonwedge", {}), ("pepperoni", "pepperoni", {}),
        ("salami", "pepperoni", {"color": "#9e2b25"}), ("thym", "zaatar", {}), ("keshek", "zaatar", {"color": "#c9a46a"}),
        ("thon", "dice", {"color": "#c9a38a"}), ("legumes", "veggies", {}), ("ice cream", "scoop", {}), ("glace", "scoop", {}),
        ("chantilly", "cream", {}), ("fruits", "fruitdice", {}), ("ananas", "fruitdice", {"color": "#f3d04a"}),
        ("amandes", "flecks", {"color": "#e8d3a8", "n": 16, "spread": 0.2}), ("noisettes", "flecks", {"color": "#8a5a2a", "n": 16, "spread": 0.2}),
        ("pepites de chocolat", "flecks", {"color": "#3a1d0b", "n": 20, "spread": 0.2}), ("achta", "cream", {"color": "#fbf3df"}),
        ("miel", "honey", {}), ("banane", "banana", {}), ("avocat", "fruitdice", {"color": "#9cc25a"}),
        ("mousse au chocolat", "cream", {"color": "#5a3018"}), ("kiwi", "fruitdice", {"color": "#8bbf3a"}),
        ("mangue", "fruitdice", {"color": "#f2a91a"}), ("pomme", "fruitdice", {"color": "#e8e0a0"}),
    ]
    for k, p, o in table:
        if k in n: return p, o
    return None, {}

def ingredients(text, kit, required_first=True, required_all=False):
    out = []
    for i, raw in enumerate([s.strip() for s in re.split(r",| et (?=[a-zé])", text) if s.strip()]):
        name = raw[0].upper() + raw[1:]
        p, o = part_for(raw, kit)
        d = {"id": slug(raw)[:24] or f"i{i}", "name": name}
        if p: d["p"] = p
        if o: d["o"] = o
        low = raw.lower()
        if required_all or (required_first and i == 0) or low.startswith("jus") or low in ("lait",):
            d["required"] = True
        out.append(d)
    # ids uniques
    seen = set()
    for d in out:
        while d["id"] in seen: d["id"] += "x"
        seen.add(d["id"])
    return out

def sz(*pairs):
    return [{"id": slug(l) or "u", "label": l, "price": p} for l, p in pairs if p]

D = []
def add(cat, name, sizes, desc="", kit="wrap", ingr=None, tags=(), photo=None, extras=None, o=None, ingr_list=None):
    if isinstance(sizes, int): sizes = sz(("", sizes))
    d = {"id": slug(cat + "-" + name)[:48], "category": cat, "name": name, "desc": desc, "sizes": sizes, "kit": kit}
    d["ingredients"] = ingr_list if ingr_list is not None else (ingredients(ingr, kit) if ingr else [])
    if tags: d["tags"] = list(tags)
    if photo: d["photo"] = f"img/{photo}.jpg"
    if extras: d["extras"] = extras
    if o: d["o"] = o
    D.append(d)

POP, VEG = "populaire", "vegetarien"
SPV = lambda s, p=None, pl=None: sz(("Sandwich", s), ("Petit", p), ("Plat", pl))

# ---------- SHAWARMA ----------
NOTE_PLAT = "Les plats sont accompagnés de hummus, frites, cornichons, salade de choux, sauce tahiné ou crème d'ail."
for nm, main, mk in [("Shawarma viande", "Viande shawarma", 4500), ("Shawarma poulet", "Poulet shawarma", 4500), ("Shawarma mixte", "Viande et poulet shawarma", 6500)]:
    pl = 7500 if "mixte" in nm else 7000
    il = [{"id": "main", "name": main, "p": "strips", "o": {"color": "#8a4a2a" if "viande" in nm.lower() else "#c98a3c"}, "required": True}]
    if "mixte" in nm: il[0]["o"] = {"color": "#8a4a2a"}; il.append({"id": "poulet", "name": "Poulet shawarma", "p": "strips", "o": {"color": "#c98a3c"}, "required": True}); il[0]["name"] = "Viande shawarma"
    il += [{"id": "cornichons", "name": "Cornichons", "p": "pickles"}, {"id": "tahine", "name": "Sauce tahiné", "p": "ramekin", "o": {"color": "#d9c39a"}}, {"id": "ail", "name": "Crème d'ail", "p": "ramekin", "o": {"color": "#f7f3ea"}}]
    add("shawarma", nm, sz(("Sandwich", 2500), ("Baguette", 3500), ("Markouk", mk), ("Plat", pl), ("½ dz pain soirée", 3500), ("1 dz pain soirée", 7000)),
        NOTE_PLAT, "wrap", ingr_list=il, tags=(POP,) if "mixte" in nm else ())

# ---------- MEZZEH ----------
V = "Accompagné d'un plat de légumes frais"
def mz(name, price, main, mo=None, desc="", tags=(), photo=None, sides=(), sizes=None):
    il = [{"id": "main", "name": main, "p": mo[0], "o": mo[1], "required": True}] if mo else [{"id": "main", "name": main, "required": True}]
    for s in sides:
        p, o = part_for(s, "mezze"); il.append({"id": slug(s), "name": s, **({"p": p} if p else {}), **({"o": o} if o else {})})
    add("mezzeh", name, sizes or price, desc, "mezze", ingr_list=il, tags=tags, photo=photo)
mz("Hummus", 4000, "Hummus", ("hummus", {}), V, (VEG,), sides=("Légumes frais",))
mz("Hummus à la viande de bœuf", 6000, "Hummus", ("hummus", {}), V, sides=("Viande de bœuf", "Légumes frais"))
mz("Hummus avec shawarma", 6000, "Hummus", ("hummus", {}), "", sides=("Shawarma",))
D[-1]["ingredients"][1].update({"p": "strips", "o": {"color": "#8a4a2a", "n": 10, "spread": 0.2}, "required": True})
D[-2]["ingredients"][1].update({"p": "meat", "o": {"n": 7, "spread": 0.18, "color": "#6b3a1e"}, "required": True})
mz("Moutabbal", 4000, "Moutabbal", ("hummus", {"color": "#cdb48e"}), V, (VEG,), "moutabbal", sides=("Légumes frais",))
mz("Batata harra", 4000, "Pommes de terre au chili", ("potato", {}), "Pommes de terre sautées au piment.", (POP, VEG))
mz("Ailes de poulet à la provençale", 6000, "Ailes de poulet", ("wings", {}))
mz("Hendbeh", 4000, "Chicorée sautée", ("greens", {}), "Chicorée sautée.", (VEG,))
mz("Feuilles de vigne farcies aux légumes", 5000, "Feuilles de vigne farcies", ("dolma", {"n": 12}), "12 pièces.", (VEG,))
mz("Sambousek à la viande", 3500, "Sambousek", ("sambousek", {}), "6 pièces.")
mz("Rouleaux de fromage", 3500, "Rouleaux de fromage", ("rolls", {}), "6 pièces.", (VEG,), "rouleaux-fromage")
mz("Kebbeh à la viande", 3500, "Kebbeh", ("kebbeh", {}), "6 pièces.", photo="kebbeh")
mz("Frites", 0, "Frites", ("fries", {"n": 30, "spread": 0.4}), sizes=sz(("Portion", 3000), ("Petite portion", 1500)))

# ---------- SALADES ----------
SAL = [("Rocca et thym", 5000, "Roquette, thym", (VEG,)), ("Rocca", 5000, "Roquette", (VEG,)),
       ("Tabbouleh", 5000, "Persil, tomate, oignon, boulgour, citron", (VEG,)),
       ("Fattouch", 5000, "Laitue, tomate, concombre, radis, pain grillé, sumac", (POP, VEG)),
       ("Salade orientale", 5000, "Laitue, tomate, concombre, oignon", (VEG,)), ("Salade de choux", 2000, "Chou", (VEG,)),
       ("Salade de crabe", 6000, "Crabe, laitue", ()), ("Salade de crabe et de crevettes", 6000, "Crabe, crevettes, laitue", ()),
       ("Salade grecque", 5000, "Laitue, tomate, concombre, fromage, olives", (VEG,)), ("Makdous halloumi salad", 7000, "Halloumi, makdous, laitue", ()),
       ("Frikeh salad", 6500, "Frikeh, laitue", ()), ("Agha salad", 6500, "Salade de la maison", ())]
for nm, pr, comp, tg in SAL:
    il = []
    for c in comp.split(", "):
        p, o = part_for(c, "salad")
        extra = {"roquette": ("lettuce", {"color": "#3f7d24", "n": 16, "spread": 0.5}), "persil": ("flecks", {"color": "#2f7a22", "n": 120, "spread": 0.5, "h": 0.08}),
                 "boulgour": ("flecks", {"color": "#d9b97a", "n": 60, "spread": 0.45, "h": 0.07}), "pain grillé": ("dice", {"color": "#d9a04a", "size": 0.06, "n": 12, "spread": 0.45, "h": 0.1}),
                 "sumac": ("flecks", {"color": "#7a1f2b", "n": 50, "spread": 0.5, "h": 0.15}), "chou": ("coleslaw", {"spread": 0.5}),
                 "halloumi": ("halloumi", {}), "makdous": ("makdous", {}), "frikeh": ("flecks", {"color": "#7a5a2a", "n": 140, "spread": 0.45, "h": 0.07}),
                 "thym": ("flecks", {"color": "#4a6a2a", "n": 60, "spread": 0.45, "h": 0.12}), "salade de la maison": ("lettuce", {"n": 14, "spread": 0.5}),
                 "crevettes": ("shrimp", {"n": 8, "spread": 0.35}), "crabe": ("dice", {"color": "#f2c4b5", "size": 0.06, "n": 12, "spread": 0.35, "h": 0.1})}.get(c.lower())
        if extra: p, o = extra
        o = dict(o or {}); o.setdefault("spread", 0.5); o.setdefault("n", 14)
        il.append({"id": slug(c), "name": c[0].upper() + c[1:], **({"p": p} if p else {}), "o": o})
    il[0]["required"] = True
    add("salades", nm, pr, "", "salad", ingr_list=il, tags=tg)
# composition des salades = déduite du nom : signaler
for d in D:
    if d["category"] == "salades": d["inferred"] = True

# ---------- BOEUF ----------
for nm, s, p, pl, comp, tg in [
    ("Langue", 3500, None, None, "Langue, tomates, cornichons, crème d'ail", ()),
    ("Cervelle", 3500, None, 6000, "Cervelle, tomates, cornichons, crème d'ail, feuilles de menthe", ()),
    ("Makanek", 3500, None, 6000, "Makanek, tomates, cornichons", (POP,)),
    ("Sojok", 3500, None, 6000, "Sojok, tomates, cornichons", ()),
    ("Philadelphia", 5000, None, 8000, "Viande, oignons, poivrons, champignons frais, mayonnaise, mozzarella", ()),
    ("Rosto", 4000, 2000, 7000, "Roti, tomates, cornichons, mayonnaise, feuilles de menthe", (POP,)),
    ("Steak (pimenté)", 4000, None, 8000, "Steak, mayonnaise, cornichons, laitue", ()),
    ("Hot dog", 3500, 2000, None, "Hot dog, sauce cocktail, cornichons, maïs, laitue", ())]:
    add("boeuf", nm, SPV(s, p, pl), comp + ".", "wrap", comp, tg)

# ---------- POULET ----------
for nm, s, p, pl, comp, tg in [
    ("Poulet classique", 3500, 2000, None, "Poulet, cornichons, crème d'ail", ()),
    ("Francisco", 4000, None, 8000, "Blanc de poulet, mozzarella, cornichons, laitue, mayonnaise", ()),
    ("Fajita", 5000, None, 8000, "Blanc de poulet, poivrons, oignons, mozzarella, sauce d'avocat", ()),
    ("Mexican", 4000, None, 8000, "Blanc de poulet, cornichons, laitue, mayonnaise, mozzarella", ()),
    ("Chicken sub", 4000, None, 8000, "Blanc de poulet, mozzarella, maïs, cornichons, crème d'ail, laitue", (POP,)),
    ("Escalope de poulet", 4000, None, None, "Blanc de poulet, frites, ketchup, salade de choux", ()),
    ("Crispy", 4000, None, None, "Blanc de poulet, ketchup, salade de choux", ()),
    ("Poulet pimenté", 3500, None, 7000, "Blanc de poulet, mayonnaise, laitue, maïs, cornichons", (POP,)),
    ("Poulet barbecue", 3500, None, 7000, "Blanc de poulet, sauce barbecue, laitue, maïs, cornichons, mayonnaise", ()),
    ("Poulet et avocat", 3500, None, 7000, "Blanc de poulet, sauce d'avocat, laitue, maïs, cornichons", ()),
    ("Foie de poulet", 3500, None, 7000, "Foie, cornichons, crème d'ail, tomates, feuille de menthe", ())]:
    add("poulet", nm, SPV(s, p, pl), comp + ".", "wrap", comp, tg)

# ---------- FRUITS DE MER ----------
for nm, s, p, comp, tg in [
    ("Poisson pimenté", 5000, None, "Filet de poisson, cornichons, laitue, sauce de poisson pimenté", ()),
    ("Filet de poisson", 5000, 2000, "Filet de poisson, cornichons, laitue, tartare", ()),
    ("Poisson pané", 5000, None, "Poisson pané, cornichons, laitue, tartare", ()),
    ("Crevettes", 5000, 2000, "Crevettes, sauce cocktail, cornichons, laitue, tartare", (POP,)),
    ("Crevettes et poulet", 5000, None, "Crevettes, blanc de poulet, cornichons, laitue, mayonnaise, tartare", ()),
    ("Calamars", 5000, None, "Calamars, tartare, cornichons, laitue, citron", ()),
    ("Crabe", 5000, 2000, "Crabe, tartare, cornichons, laitue, citron", ()),
    ("Crevettes et calamars", 5000, None, "Crevettes, calamars, tartare, cornichons, laitue, citron", (POP,)),
    ("Crevettes et crabe", 5000, None, "Crevettes, crabe, tartare, cornichons, laitue, citron", ())]:
    add("mer", nm, SPV(s, p, 9000), comp + ".", "wrap", comp, tg)
    if nm.startswith("Crevettes et"): D[-1]["ingredients"][1]["required"] = True

# ---------- SANDWICHS ----------
for nm, s, p, comp, tg in [
    ("Mortadelle bœuf ou poulet", 3000, 2000, "Mortadelle, laitue, cornichons, mayonnaise, mozzarella", ()),
    ("Sandwich de frites", 3000, None, "Frites, salade mayonnaise, ketchup", (VEG,)),
    ("Sandwich batata harra", 2000, None, "Pommes de terre au chili, tomates, cornichons, citron, sel", (VEG,)),
    ("Sandwich de feuilles de vigne farcies", 2000, None, "Feuilles de vigne farcies aux légumes, citron, sel", (VEG,)),
    ("Sandwich de hendbeh", 2000, None, "Chicorée sautée, citron, sel", (VEG,)),
    ("Sandwich de kashkaval", 3000, 2000, "Kashkaval", (VEG,)),
    ("Sandwich de labneh", 3000, 2000, "Labneh, olives, concombre, tomate, feuilles de menthe", (VEG,))]:
    add("sandwichs", nm, SPV(s, p), comp + ".", "wrap", comp, tg)
for d in D:
    if d["category"] in ("sandwichs", "boeuf", "poulet", "mer"):
        for i in d["ingredients"]:
            if i.get("p") in ("dolma", "potato", "greens", "fries", "falafel"): i["o"] = {**i.get("o", {}), "end": True}

# ---------- BURGERS ----------
for nm, b, pl, meat in [("Hamburger", 4000, 5000, "b"), ("Cheese burger", 4500, 5500, "b"), ("Hamburger avec oeufs", 5000, 6000, "b"),
                        ("Cheese burger avec oeufs", 5500, 6500, "b"), ("Double burger", 5500, 6500, "b"), ("Double extra burger", 5500, 7000, "b"),
                        ("Chicken burger", 4000, 5000, "c"), ("Chicken cheese burger", 4500, 5500, "c"), ("Double chicken burger", 5500, 6500, "c"), ("Zinger", 6000, 7000, "c")]:
    il = [{"id": "steak", "name": "Steak de bœuf" if meat == "b" else "Filet de poulet pané", "p": "patty", "o": {"color": "#5a2a12" if meat == "b" else "#d9a04a", "double": "ouble" in nm}, "required": True}]
    if "heese" in nm: il.append({"id": "fromage", "name": "Fromage", "p": "cheeseslice"})
    if "oeufs" in nm: il.append({"id": "oeuf", "name": "Œuf", "p": "friedegg"})
    add("burgers", nm.replace("oeufs", "œufs"), sz(("Burger", b), ("Plat", pl)), "Le plat est servi avec des frites." if False else "", "burger", ingr_list=il, photo="zinger" if nm == "Zinger" else None)

# ---------- FALAFEL ----------
add("falafel", "Sandwich falafel", 1500, "Falafel, biwaz mix, sauce tahiné, tomates, radis.", "wrap", "Falafel, biwaz mix, sauce tahiné, tomates, radis", (VEG,))
add("falafel", "Sandwich falafel extra", 2000, "1 morceau extra de falafel, biwaz mix, sauce tahiné, tomates, radis.", "wrap", "Falafel, biwaz mix, sauce tahiné, tomates, radis", (VEG,))
for d in D[-2:]:
    d["ingredients"][0]["o"] = {"end": True, "n": 3}
add("falafel", "½ dz de falafel", 3000, "6 pièces de falafel, sauce tahiné, légumes.", "mezze", ingr_list=[
    {"id": "falafel", "name": "Falafel (6 pièces)", "p": "falafel", "o": {"n": 6, "spread": 0.34}, "required": True},
    {"id": "tahine", "name": "Sauce tahiné", "p": "ramekin", "o": {"color": "#d9c39a"}}, {"id": "legumes", "name": "Légumes", "p": "veggies"}], tags=(POP, VEG))
add("falafel", "1 dz de falafel", 6000, "12 pièces de falafel, sauce tahiné, légumes.", "mezze", ingr_list=[
    {"id": "falafel", "name": "Falafel (12 pièces)", "p": "falafel", "o": {"n": 12, "spread": 0.4, "rings": True}, "required": True},
    {"id": "tahine", "name": "Sauce tahiné", "p": "ramekin", "o": {"color": "#d9c39a"}}, {"id": "legumes", "name": "Légumes", "p": "veggies"}], tags=(VEG,))
add("falafel", "Boîte de sauce tahiné", sz(("Petite", 1000), ("Grande", 2000)), "", "mezze", ingr_list=[{"id": "tahine", "name": "Sauce tahiné", "p": "ramekin", "o": {"color": "#d9c39a", "big": True}, "required": True}])

# ---------- PLATS / BRAISÉ ----------
ACC = [("Hummus", "ramekin", {"color": "#e3cc9a"}), ("Frites", "fries", {}), ("Cornichons", "pickles", {}), ("Salade de choux", "coleslaw", {}),
       ("Sauce tahiné", "ramekin", {"color": "#d9c39a"}), ("Crème d'ail", "ramekin", {"color": "#f7f3ea"})]
def acc(lst): return [{"id": slug(n), "name": n, "p": p, "o": o} for n, p, o in lst]
for nm, pr, main, part, o in [("Escalope de poulet", 7000, "Escalope de poulet", "cutlet", {}), ("Poulet broasted (4 pièces)", 7500, "Poulet broasted", "wings", {"n": 4, "big": True}),
                              ("Crispy poulet pimenté (6 pièces)", 7500, "Crispy poulet pimenté", "tenders", {"color": "#b5541e"}), ("Crispy (6 pièces)", 7500, "Crispy", "tenders", {})]:
    add("plats", nm, pr, NOTE_PLAT, "plate", ingr_list=[{"id": "main", "name": main, "p": part, "o": o, "required": True}] + acc(ACC))
for nm, pr in [("½ poulet braisé", 5500), ("1 poulet braisé", 11000)]:
    add("braise", nm, pr, "Accompagné de légumes, hummus, cornichons, crème d'ail et frites.", "plate", ingr_list=[
        {"id": "poulet", "name": "Poulet braisé", "p": "roastchicken", "o": {"half": nm.startswith("½")}, "required": True}] +
        acc([("Légumes", "veggies", {}), ("Hummus", "ramekin", {"color": "#e3cc9a"}), ("Cornichons", "pickles", {}), ("Crème d'ail", "ramekin", {"color": "#f7f3ea"}), ("Frites", "fries", {})]))

# ---------- GRILLADES ----------
GR = [("Shish taouk", 3500, 6000, 10000, 20000, "skewer", {"color": "#c98a3c"}, "shish-taouk"),
      ("Ailes de poulet", None, 6000, None, None, "wings", {}, None),
      ("Viande grillée", 3500, 6000, 10000, 20000, "skewer", {"color": "#6b3a1e"}, None),
      ("Kabab halaby", 3500, 6000, 10000, 20000, "kofta", {}, None), ("Kabab orfali", 4000, 6000, 10000, 20000, "kofta", {"veg": "#7a3a6a"}, None),
      ("Kabab kheshkhash", 3500, 6000, 10000, 20000, "kofta", {"sauce": True}, None), ("Kabab aubergines", 4000, 6000, 10000, 20000, "kofta", {"veg": "#4a2a4a"}, None),
      ("Kabab istanbouly", 4000, 6000, 10000, 20000, "kofta", {"veg": "#d63a2a"}, None), ("Kabab champignons", 4000, 6000, 10000, 20000, "kofta", {"veg": "#d9c7a8"}, None),
      ("Kabab poulet", 3500, 6000, 10000, 20000, "kofta", {"color": "#c98a3c"}, None), ("Habra grillée", 3000, 5000, None, None, "skewer", {"color": "#7a2a1a"}, None),
      ("Kebbeh grillée", 4000, 6000, None, None, "kebbeh", {"flat": True}, None), ("Makanek", 3500, 6000, None, None, "sausage", {"color": "#7a3418", "n": 10, "spread": 0.35}, None),
      ("Sojok", 3500, 6000, None, None, "sausage", {"color": "#8f2a18", "n": 10, "spread": 0.35}, None),
      ("Plat spécialité Agha", None, 7000, None, None, "skewer", {"mixed": True}, None), ("Plat de côtelettes", None, 6000, None, None, "chops", {}, None),
      ("Grillades variées", None, None, 10000, 20000, "skewer", {"mixed": True}, None)]
for nm, s, pl, hk, k, part, o, ph in GR:
    add("grillades", nm, sz(("Sandwich", s), ("Plat", pl), ("½ kilo", hk), ("Kilo", k)), "", "grill", ingr_list=[{"id": "main", "name": nm, "p": part, "o": o, "required": True}], photo=ph)

# ---------- VIANDE CRUE ----------
for nm in ["Malsa", "Frakeh", "Kebbeh"]:
    add("crue", nm, sz(("Plat", 6000)), "", "plate", ingr_list=[{"id": "main", "name": nm, "p": "raw", "o": {"kebbeh": nm == "Kebbeh"}, "required": True}])

# ---------- MINI'S ----------
add("minis", "Mini pizza", sz(("½ dz soirée", 2000), ("1 dz soirée", 4000)), "", "mezze", ingr_list=[{"id": "main", "name": "Mini pizzas", "p": "minipizza", "required": True}], photo="mini-pizza")
add("minis", "Sfiha", sz(("½ dz soirée", 2000), ("1 dz soirée", 4000)), "", "mezze", ingr_list=[{"id": "main", "name": "Sfiha à la viande", "p": "sfiha", "required": True}], photo="sfiha")
add("minis", "Fatayer épinards", sz(("½ dz", 1500), ("1 dz", 3000)), "", "mezze", ingr_list=[{"id": "main", "name": "Fatayer aux épinards", "p": "fatayer", "required": True}], tags=(VEG,), photo="fatayer")

# ---------- PIZZAS ----------
ADD = [("Mortadelle de poulet", "strips", {"color": "#eaa9a3", "n": 10, "spread": 0.6}), ("Mortadelle de bœuf", "strips", {"color": "#d98a8a", "n": 10, "spread": 0.6}),
       ("Saucisses", "sausage", {"color": "#c46a3a", "n": 10, "spread": 0.6, "flat": True}), ("Salami", "pepperoni", {"color": "#9e2b25"}), ("Pepperoni", "pepperoni", {}),
       ("Sojok", "sausage", {"color": "#8f2a18", "n": 10, "spread": 0.6, "flat": True}), ("Rôti de bœuf", "strips", {"color": "#8a4a2a", "n": 12, "spread": 0.6}),
       ("Thon", "dice", {"color": "#c9a38a", "n": 18, "spread": 0.6, "h": 0.08}), ("Filet de poisson", "strips", {"color": "#efd29a", "n": 10, "spread": 0.6}),
       ("Crevettes", "shrimp", {"n": 8, "spread": 0.6}), ("Oignons", "onion", {"spread": 0.6, "n": 10}), ("Maïs", "dice", {"color": "#f4c430", "size": 0.03, "n": 40, "spread": 0.65, "h": 0.08})]
PZ_EX = [{"id": "add-" + slug(n), "name": n, "price": {"p": 1000, "m": 1500, "g": 2000}, "p": p, "o": {**o, "pz": True}} for n, p, o in ADD]
for nm, p, m, g, comp, tg, ph in [
    ("Pizza reine", 3500, 6500, 9000, "Fromage, champignons, olives", (VEG,), None),
    ("Pizza 4 fromages", 3500, 6500, 9000, "Sauce tomate, roquefort, fromage de chèvre, mozzarella, fondel", (VEG,), None),
    ("Pizza végétarienne", 3500, 6500, 9000, "Sauce tomate, poivrons, champignons, maïs, olives, mozzarella", (VEG,), "pizza-vegetarienne"),
    ("Pizza marguerita", 3000, 5000, 8000, "Sauce tomate, mozzarella", (VEG,), None),
    ("Pizza pepperoni", 3500, 6500, 9000, "Sauce tomate, pepperoni, mozzarella", (), "pizza-pepperoni")]:
    il = ingredients(comp, "pizza", required_first=False)
    for i in il:
        if i["name"].lower().startswith("sauce tomate"): i.update({"p": "disc", "o": {"R": 0.86, "color": "#b8321f", "h": 0.045}})
        if i.get("p") == "dice" and "maïs" in i["name"].lower(): i["o"] = {"color": "#f4c430", "size": 0.03, "n": 40, "spread": 0.65, "h": 0.08}
        if i.get("p") == "cheese": i.setdefault("o", {})
    add("pizzas", nm, sz(("P", p), ("M", m), ("G", g)), comp + ".", "pizza", ingr_list=il, tags=tg, photo=ph, extras=PZ_EX)
for d in D:
    if d["category"] == "pizzas":
        for i in d["ingredients"]:
            if i.get("p") == "cheese": i["o"] = {**i.get("o", {}), "n": 18}

# ---------- MANAKICH ----------
MK = [("Mankoushi viande", None, 2000, "Viande"), ("Fromage", 2000, 2500, "Fromage"), ("Fromage double", 3000, 3500, "Double fromage"),
      ("Fromage et sojok", 2500, 3000, "Fromage, sojok"), ("Thym", 1000, 1500, "Thym"), ("Thym et labneh", 1500, 2000, "Thym, labneh"),
      ("Cocktail thym et fromage", 2000, 2500, "Thym, fromage"), ("Moitié fromage moitié thym", 2000, 2500, "Fromage, thym"),
      ("Keshek", 2000, 2500, "Keshek"), ("Labneh", 1500, 2000, "Labneh"), ("Kashkaval", 2500, 3000, "Kashkaval"),
      ("Fromage et mortadelle", 3000, 3500, "Fromage, mortadelle"), ("Fromage et dinde", 3000, 3500, "Fromage, dinde"),
      ("Viande et fromage", 2500, 3000, "Viande, fromage"), ("Kafta", 2000, 2500, "Kafta"), ("Kafta et fromage", 2500, 3000, "Kafta, fromage"),
      ("Sojok", 2000, 2500, "Sojok"), ("Oignons et tomates", 1500, 2000, "Oignons, tomates"), ("Oignons et tomates avec fromage", 2500, 3000, "Oignons, tomates, fromage")]
PH = {"Mankoushi viande": "mankoushi-viande", "Fromage": "mankoushi-fromage", "Thym": "mankoushi-thym"}
for nm, r, f, comp in MK:
    il = []
    for i, c in enumerate(comp.split(", ")):
        cl = c.lower()
        if cl == "viande": p, o = "mince", {}
        elif "fromage" in cl or cl == "kashkaval": p, o = "cheese", {"n": 26, "color": "#f6e3a1" if cl != "kashkaval" else "#f2d47a"}
        elif cl in ("thym",): p, o = "zaatar", {}
        elif cl == "keshek": p, o = "zaatar", {"color": "#c9a46a"}
        elif cl == "labneh": p, o = "dollop", {"color": "#fbf7ee", "n": 9}
        elif cl == "sojok": p, o = "pepperoni", {"color": "#8f2a18"}
        elif cl == "mortadelle": p, o = "pepperoni", {"color": "#eaa9a3", "r": 0.12}
        elif cl == "dinde": p, o = "pepperoni", {"color": "#e8c3a8", "r": 0.12}
        elif cl == "kafta": p, o = "mince", {"color": "#6b3a1e"}
        elif cl == "oignons": p, o = "onion", {"spread": 0.6, "n": 10}
        elif cl == "tomates": p, o = "dice", {"color": "#d63a2a", "n": 26, "spread": 0.65, "h": 0.06}
        else: p, o = None, {}
        if "moitié" in nm.lower(): o = {**o, "half": 1 if i == 0 else -1}
        il.append({"id": slug(c), "name": c, "p": p, "o": o, **({"required": True} if i == 0 else {})})
    add("manakich", nm if nm.startswith("Mankoushi") else "Manouché " + nm.lower(), sz(("Régulier", r), ("Fin", f)), "", "manakish", ingr_list=il,
        tags=(VEG,) if not any(x in comp.lower() for x in ("viande", "sojok", "mortadelle", "dinde", "kafta")) else (), photo=PH.get(nm))

# ---------- DESSERTS & GLACES ----------
for nm, pr, comp, part in [("Chocolat mou", 4000, "Ice cream chocolat, fruits secs, pépites de chocolat, crème chantilly", None),
                           ("Banana split", 5500, "3 boules de glace, bananes fraîches, crème chantilly", None),
                           ("Salade de fruits frais", 5500, "Ananas, kiwi, mangue, banane, pomme, fruit de la passion, achta, miel", None),
                           ("Achta plat", 6000, "Achta, miel, amandes", None)]:
    il = ingredients(comp, "dessert")
    for i in il:
        n = i["name"].lower()
        if "ice cream chocolat" in n: i.update({"p": "scoop", "o": {"color": "#5a3018", "n": 3}})
        if "boules de glace" in n: i.update({"p": "scoop", "o": {"n": 3, "mixed": True}})
        if "fruits secs" in n: i.update({"p": "flecks", "o": {"color": "#a0703a", "n": 20, "spread": 0.2}})
        if "fruit de la passion" in n: i.update({"p": "fruitdice", "o": {"color": "#e8b030"}})
    add("desserts", nm, pr, comp + ".", "dessert", ingr_list=il)
for nm, pr, col in [("Custard", 1000, "#f2d27a"), ("Riz au lait", 1000, "#f6efdc"), ("Mouhalabieh", 1000, "#fbf6ea")]:
    add("desserts", nm, pr, "", "dessert", ingr_list=[{"id": "main", "name": nm, "p": "pudding", "o": {"color": col}, "required": True}])
for nm, pr, n in [("Crème glacée", 2000, 2), ("Boule de glace", 1000, 1), ("½ kilo de glace", 4500, 5), ("1 kilo de glace", 9000, 7)]:
    add("desserts", nm, pr, "", "dessert", ingr_list=[{"id": "main", "name": "Glace", "p": "scoop", "o": {"n": n, "mixed": True}, "required": True}], photo="glaces")
add("desserts", "Gâteau fait maison", sz(("La pièce", 3500)), "", "dessert", ingr_list=[{"id": "main", "name": "Gâteau", "p": "cake", "required": True}])

# ---------- MILKSHAKES / JUS / COCKTAILS ----------
def drink(cat, nm, pr, comp, color, tags=(), photo=None):
    il = ingredients(comp, "glass", required_first=False) if comp else []
    for i in il:
        n = i["name"].lower()
        if n.startswith("ice cream"): i.update({"p": "scoop", "o": {"color": "#5a3018" if "chocolat" in n else "#f4a3b4" if "fraise" in n else "#f6ead0"}})
        if n.startswith("jus") or n in ("lait",): i["required"] = True; i.pop("p", None); i.pop("o", None)
    add(cat, nm, pr, (comp + ".") if comp else "", "glass", ingr_list=il, tags=tags, photo=photo, o={"color": color})
for nm, comp, col, tg in [("Milkshake chocolat", "Ice cream, pépites de chocolat, noisettes", "#6b3a1e", (POP,)),
                          ("Milkshake fraise", "Ice cream, jus de fraise, sauce fraise, noisettes", "#f08aa0", ()),
                          ("Milkshake mangue", "Ice cream, jus de mangue, sauce mangue, noisettes", "#f5b43a", ())]:
    drink("milkshakes", nm, 4000, comp, col, tg)
JUS = [("Mangue", 3000, "#f5a623"), ("Goyave", 3000, "#f28b82"), ("Fraise", 3000, "#e8394a"), ("Carotte", 3000, "#f07a1a"), ("Limonade", 3000, "#f3e98a"),
       ("Ananas", 3000, "#f6d54a"), ("Jallab", 2000, "#5a1a10"), ("Pomme", 3000, "#e8d27a"), ("Cocktail", 4000, "#f29a4a"), ("Lait et banane", 3000, "#f6ecc8"),
       ("Melon", 3000, "#f5b97a"), ("Orange", 3000, "#f7941d"), ("Pamplemousse", 3000, "#f47a6a"), ("Fraise et banane", 3000, "#f39aa0"),
       ("Orange et carotte", 3000, "#f5821f"), ("Avocat", 3500, "#a8c95a")]
for nm, pr, col in JUS:
    add("jus", "Jus " + nm.lower() if nm not in ("Cocktail", "Limonade", "Jallab") else nm, pr, "Pressé minute.", "glass",
        ingr_list=[{"id": "glacons", "name": "Glaçons", "p": "ice"}], o={"color": col})
CK = [("Cocktail de fruits", 5000, "Jus de goyave, jus de mangue, jus de fraise, fruits mix", "#f0705a", (), "cocktail-fruits"),
      ("Kazanova avocat", 5000, "Jus d'avocat, pépites de chocolat, mousse au chocolat", "#a8c95a", (), None),
      ("Cocktail avocat et fruits exotiques", 5000, "Jus d'avocat, jus de fraise, jus de mangue, achta, amandes, miel", "#a8c95a", (POP,), "cocktail-avocat"),
      ("Appolo", 5000, "Achta, amandes, miel, jus d'avocat, fruits mix, jus de fraise, crème chantilly", "#b9c96a", (), None),
      ("Vermosa", 5000, "Jus cocktail, bananes, achta, amandes, miel", "#f29a4a", (), None),
      ("Napoléon", 5000, "Jus cocktail, achta, amandes, miel, jus de mangue", "#f5a623", (), None),
      ("Tahiti", 5500, "Bananes, morceaux d'ananas, jus de fraise, amandes, ice cream fraise, lait", "#f39aa0", (POP,), None),
      ("Mandella", 5000, "Bananes, crème chantilly, pépites de chocolat, ice cream chocolat", "#e8c890", (), None),
      ("Norega", 5500, "Achta, amandes, miel, fruits mix, jus de mangue, crème chantilly", "#f5a623", (), None),
      ("Hitler", 5000, "Morceaux d'ananas, jus de mangue, jus de fraise, amandes, ice cream", "#f2805a", (), None),
      ("Miami", 5000, "Ice cream chocolat, lait, fruits mix, jus de fraise, crème chantilly", "#d9826a", (), None),
      ("Zololo", 5000, "Jus de fraise, fruits mix, ice cream", "#e8394a", (), None),
      ("Elizabeth", 5000, "Achta, amandes, miel, avocat, jus de mangue, fruits, crème chantilly", "#d9b84a", (), None),
      ("Panama", 5500, "Ice cream fraise, lait, fruits mix, jus de mangue, crème chantilly", "#f5b97a", (), None),
      ("Aloha", 5000, "Bananes, fruits mix, jus de fraise, achta, amandes, miel, ice cream", "#f0807a", (), None),
      ("Exotica", 5500, "Avocat, fruits mixtes, jus mixtes, achta, miel", "#b9c96a", (), None)]
for nm, pr, comp, col, tg, ph in CK:
    drink("cocktails", nm, pr, comp, col, tg, ph)

# ---------- BOISSONS ----------
for nm, pr, kit, col in [("Eau", 1000, "bottle", "#cfe8f5"), ("Eau grand", 1500, "bottle", "#cfe8f5"), ("Laban Agha", 1500, "glass", "#f8f6ef"), ("Laban ayran", 1000, "glass", "#f8f6ef"),
                         ("Energy drink", 1500, "can", "#2a5ad8"), ("Iced tea", 1500, "can", "#e3a21a"), ("Coca-Cola", 1000, "can", "#d0101a"), ("Fanta", 1000, "can", "#f27a0a"),
                         ("Sprite", 1000, "can", "#1a9a4a"), ("Perrier", 1500, "bottle", "#2f8a3a"),
                         ("Café latte", 2000, "cup", "#c89a6a"), ("Café macchiato", 2000, "cup", "#a8784a"), ("Cappuccino", 2000, "cup", "#c8a07a"), ("Chocolat chaud", 2000, "cup", "#5a3018"),
                         ("Espresso", 1500, "cup", "#3a1d0b"), ("Espresso double", 2500, "cup", "#3a1d0b"), ("Lait", 1000, "cup", "#f8f6ef"), ("Thé", 1000, "cup", "#a8501a"),
                         ("Thé au lait", 1500, "cup", "#c8946a"), ("Thé aromatisé", 1500, "cup", "#b8601a")]:
    il = [{"id": "glacons", "name": "Glaçons", "p": "ice"}] if kit == "glass" else []
    add("boissons", nm, pr, "", kit, ingr_list=il, o={"color": col, "small": kit == "cup" and "spresso" in nm})

CATS = [("mezzeh", "Mezzeh", ""), ("salades", "Salades", ""), ("boeuf", "Snack bœuf", ""), ("poulet", "Snack poulet", ""),
        ("mer", "Snack fruits de mer", "Tous les plats sont servis en large portion avec frites et pain."), ("sandwichs", "Snack divers", ""),
        ("burgers", "Burgers", ""), ("shawarma", "Shawarma", NOTE_PLAT), ("falafel", "Falafel", ""), ("plats", "Plats", NOTE_PLAT),
        ("braise", "Poulet braisé", "Le poulet braisé est accompagné de légumes, hummus, cornichons, crème d'ail et frites."),
        ("grillades", "Grillades", ""), ("crue", "Viande crue", ""), ("minis", "Mini's", ""), ("pizzas", "Pizzas", "Additions au choix selon la taille : 1 000 F (P), 1 500 F (M), 2 000 F (G)."),
        ("manakich", "Manakish", ""), ("desserts", "Desserts", ""), ("milkshakes", "Milkshakes", ""), ("jus", "Jus", ""),
        ("cocktails", "Cocktails de fruits", ""), ("boissons", "Boissons", "")]
ids = set()
for d in D:
    assert d["id"] not in ids, d["id"]; ids.add(d["id"])
menu = {"restaurant": {"name": "Agha", "tagline": "De tout cœur · Restaurant libanais", "city": "Abidjan", "whatsapp": "2250700000000",
                       "currency": "F CFA", "deliveryFee": 500, "source": "Carte Agha CI, mai 2024"},
        "categories": [{"id": c, "name": n, **({"note": t} if t else {})} for c, n, t in CATS],
        "featured": "shawarma-shawarma-mixte",
        # bannière par défaut ; le responsable la remplace en envoyant une image avec /pub au bot
        "promo": {"img": "img/promo-exemple.jpg", "alt": "Offre du moment : plat shawarma mixte", "dish": "shawarma-shawarma-mixte"}, "dishes": D}
# vraies photos des plats (img/web/, photos libres de droits + photos envoyées par le restaurant)
pj = os.path.join(os.path.dirname(__file__), "..", "menu", "photos.json")
if os.path.exists(pj):
    PICS = json.load(open(pj))
    for d in D:
        if d["id"] in PICS: d["pic"] = PICS[d["id"]]
# la photo du catalogue Agha passe avant les photos trouvées sur le net (les photos envoyées par le restaurant restent prioritaires)
for d in D:
    if d.get("photo") and "/agha-" not in d.get("pic", {}).get("src", ""): d["pic"] = {"src": d["photo"], "by": "Catalogue Agha"}
out = os.path.join(os.path.dirname(__file__), "..", "menu", "menu.json")
json.dump(menu, open(out, "w"), ensure_ascii=False, separators=(",", ":"))
from collections import Counter
print(len(D), "articles", Counter(d["category"] for d in D))
print("sans pièce 3D:", sorted({i["name"] for d in D for i in d["ingredients"] if not i.get("p")})[:80])
