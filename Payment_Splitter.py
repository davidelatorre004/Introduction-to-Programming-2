import json
import os

# Initialization of the balances "Database"
# We use a dictionary to keep track of each friend's account.
# A positive balance means the friend is owed money (Credit)
# A negative balance means the friend owes money (Debt)
friends = ["Alice", "Bob", "Charlie", "David"]
DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "balances.json")


def load_balances():
    """Load saved balances if the file exists; otherwise start at 0."""
    loaded = {friend: 0.0 for friend in friends}
    if not os.path.exists(DATA_FILE):
        return loaded
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as file:
            saved = json.load(file)
        for friend in friends:
            if friend in saved:
                loaded[friend] = float(saved[friend])
    except (json.JSONDecodeError, OSError, TypeError, ValueError):
        print("Warning: Could not read saved balances. Starting from 0.")
    return loaded


def save_balances():
    """Persist the current balances to a JSON file."""
    with open(DATA_FILE, "w", encoding="utf-8") as file:
        json.dump(balances, file, indent=2)


def show_balances():
    print("\n--- CURRENT BALANCES (Database) ---")
    for friend, balance in balances.items():
        print(f"{friend}: {balance:.2f} €")
    print("-----------------------------------\n")


def ask_amount(prompt):
    """Ask for a number until the user enters a valid amount >= 0."""
    while True:
        raw = input(prompt).strip().replace(",", ".")
        try:
            amount = float(raw)
        except ValueError:
            print("Error: Please enter a valid number.")
            continue
        if amount < 0:
            print("Error: Amount cannot be negative.")
            continue
        return amount


def show_settlement():
    """Print a simple plan of who should pay whom to reach zero."""
    print("\n--- SETTLEMENT ---")
    debtors = []
    creditors = []
    for friend, balance in balances.items():
        if balance < -0.005:
            debtors.append([friend, -balance])
        elif balance > 0.005:
            creditors.append([friend, balance])

    if not debtors and not creditors:
        print("Everyone is settled. No payments needed.")
        print("--------------------\n")
        return

    i = 0
    j = 0
    while i < len(debtors) and j < len(creditors):
        debtor, debt = debtors[i]
        creditor, credit = creditors[j]
        payment = min(debt, credit)
        print(f"{debtor} pays {creditor}: {payment:.2f} €")
        debtors[i][1] -= payment
        creditors[j][1] -= payment
        if debtors[i][1] <= 0.005:
            i += 1
        if creditors[j][1] <= 0.005:
            j += 1
    print("--------------------\n")


balances = load_balances()
print("Loaded balances from file." if os.path.exists(DATA_FILE) else "No saved file found. Starting fresh.")
show_balances()

# Start of Workflow: Main Loop
while True:
    print("\n*** START: NEW PAYMENT ***")

    # Node: Input Data
    payer = input(f"Who paid? ({', '.join(friends)}): ").strip().capitalize()

    # Basic validation to ensure the payer exists
    if payer not in friends:
        print("Error: User not found. Please try again.")
        continue

    total_amount = ask_amount("Enter the total amount: ")

    # Node: Who is involved in the expense?
    print("\nWho is involved in the expense?")
    print("1. Only Payer")
    print("2. Partial Split (2 or 3 participants)")
    print("3. Everyone (4 participants)")
    choice = input("Select an option (1/2/3): ").strip()

    beneficiaries = []
    individual_share = 0.0

    # Branches
    if choice == "1":  # Only Payer
        print("-> Individual Expense. No split.")
        beneficiaries = [payer]
        individual_share = total_amount

    elif choice == "3":  # Everyone (4)
        print("-> Total Split. Divided by 4.")
        beneficiaries = friends
        individual_share = total_amount / 4

    elif choice == "2":  # Partial Split
        n_raw = input("-> Split by 2 or 3? ").strip()
        if n_raw not in ("2", "3"):
            print("Error: Please enter 2 or 3. Transaction cancelled.")
            continue
        n_participants = int(n_raw)

        # Prompt: Select the specific participants
        print(f"Enter the names of the {n_participants} participants separated by commas:")
        input_names = input().split(",")

        # Clean up the inputted strings
        beneficiaries = [name.strip().capitalize() for name in input_names if name.strip()]

        unknown = [name for name in beneficiaries if name not in friends]
        if unknown:
            print(f"Error: Unknown name(s): {', '.join(unknown)}. Transaction cancelled.")
            continue
        if len(beneficiaries) != n_participants:
            print(f"Error: Expected {n_participants} names, got {len(beneficiaries)}. Transaction cancelled.")
            continue
        if len(set(beneficiaries)) != len(beneficiaries):
            print("Error: Duplicate names. Transaction cancelled.")
            continue

        individual_share = total_amount / n_participants

    else:
        print("Invalid option. Transaction cancelled.")
        continue

    # Node: Update Balances
    # 1. The payer gets a credit equal to the total amount advanced (Payer Credit)
    balances[payer] += total_amount

    # 2. All selected beneficiaries get a debt equal to their share (Beneficiaries Debt)
    # (If the payer is also a beneficiary, their debt offsets their credit automatically)
    for beneficiary in beneficiaries:
        balances[beneficiary] -= individual_share

    # Node: Save to Database
    save_balances()
    show_balances()

    # Node: Are there new payments to add?
    new_payment = input("Are there new payments to add? (yes/no): ").strip().lower()

    if new_payment == "no":
        # Exit: Close Application
        show_settlement()
        print("Exit: Application closed. Final summary of balances stored in balances.json.")
        break
