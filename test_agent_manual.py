from agent_core import run_agent

SESSION_ID = "prueba-local-1"

while True:
    prompt = input("Tú: ").strip()

    if prompt.lower() in {"salir", "exit"}:
        break

    result = run_agent(
        prompt=prompt,
        session_id=SESSION_ID,
    )

    print("\nAgente:")
    print(result["answer"])

    print("\nTraza:")
    print(result["trace"])
    print()