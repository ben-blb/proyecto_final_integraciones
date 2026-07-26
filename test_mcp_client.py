import asyncio

from fastmcp import Client


async def main() -> None:
    client = Client("http://127.0.0.1:8000/mcp")

    async with client:
        tools = await client.list_tools()

        print("Tools disponibles:")
        for tool in tools:
            print(f"- {tool.name}")

        result = await client.call_tool(
            "registrar_proveedor",
            {
                "nombre": "Mobiliario Central",
                "rfc": "MCE010101ABC",
                "condicion_pago": "credito",
                "dias_credito": 30,
                "confirmar": True,
            },
        )

        print("Resultado:")
        print(result)


if __name__ == "__main__":
    asyncio.run(main())