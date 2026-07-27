from __future__ import annotations

import uuid

import streamlit as st

from agent_core import run_agent


st.set_page_config(
    page_title="Asistente de Compras",
    page_icon="🧾",
    layout="wide",
)


def new_session_id() -> str:
    return f"compras-{uuid.uuid4()}"


if "session_id" not in st.session_state:
    st.session_state.session_id = new_session_id()

if "messages" not in st.session_state:
    st.session_state.messages = []


with st.sidebar:
    st.header("PoC de compras")

    st.caption("Sesión")
    st.code(st.session_state.session_id)

    if st.button(
        "Reiniciar conversación",
        use_container_width=True,
    ):
        st.session_state.session_id = new_session_id()
        st.session_state.messages = []
        st.rerun()

    st.divider()

    st.markdown(
        """
        **Incluye**

        - Proveedores
        - Requisiciones
        - Órdenes de compra
        - Facturas
        - Pagos completos
        - Trazabilidad
        - Próximos vencimientos

        **No incluye**

        - Actualización
        - Eliminación
        - Pagos parciales
        - Autorizaciones reales
        """
    )

    st.markdown(
        """
        **Flujo de ejemplo**
        1. **Crear proveedor**

        ```text
        Registra al proveedor Mobiliario Central con RFC MCE010101ABC y 30 días de crédito.
        ```

        2. **Confirmar**

        ```text
        Sí, confirma.
        ```

        3. **Crear requisición**

        ```text
        Crea una requisición para mobiliario por $18,500 MXN, solicitada por Ana Torres, del área de Operaciones, tipo Compra operativa.
        ```

        4. **Confirmar**

        ```text
        Confirma.
        ```

        5. **Crear orden**

        ```text
        Crea una orden para esa requisición usando el proveedor anterior por $18,500 MXN.
        ```

        6. **Confirmar**

        ```text
        Confirma.
        ```

        7. **Registrar factura**

        ```text
        Registra la factura F-9085 para esa orden, con fecha 2026-07-26, subtotal $18,500, impuestos $2,960 y total $21,460 MXN.
        ```

        8. **Confirmar y pagar**

        ```text
        Confirma. Después registra el pago completo por transferencia, con fecha 2026-08-20 y referencia TRX-1005.
        ```

        9. **Confirmar pago**

        ```text
        Sí, confirma el pago.
        ```

        10. **Verificar**

        ```text
        Muéstrame toda la trazabilidad de esa requisición.
        ```

        Este flujo recorre proveedor → requisición → orden → factura → pago completo. 
"""
    )


st.title("Asistente de Seguimiento de Compras y Pagos")
st.caption(
    "Prueba de concepto con Streamlit, LangChain, OpenAI, MCP y SQLite."
)


for item in st.session_state.messages:
    with st.chat_message(item["role"]):
        st.markdown(item["content"])

        if item.get("trace"):
            with st.expander(
                "Evidencia y tools utilizadas"
            ):
                st.json(item["trace"])


if prompt := st.chat_input(
    "Consulta o registra información de compras"
):
    user_item = {
        "role": "user",
        "content": prompt,
    }

    st.session_state.messages.append(user_item)

    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        try:
            with st.spinner("Procesando..."):
                result = run_agent(
                    prompt=prompt,
                    session_id=st.session_state.session_id,
                )

            st.markdown(result["answer"])

            if result["trace"]:
                with st.expander(
                    "Evidencia y tools utilizadas"
                ):
                    st.json(result["trace"])

            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "content": result["answer"],
                    "trace": result["trace"],
                }
            )

        except Exception as exc:
            error_message = (
                "No fue posible procesar la solicitud. "
                "Comprueba que el servidor MCP esté encendido."
            )

            st.error(error_message)

            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "content": error_message,
                    "trace": [
                        {
                            "tipo": "error",
                            "detalle": str(exc),
                        }
                    ],
                }
            )