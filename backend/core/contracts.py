"""Shared request/response contract execution."""

import re
import uuid

from flask import jsonify


class ContractValidationError(ValueError):
    pass


def _matches_type(value, expected):
    if expected == "object":
        return isinstance(value, dict)
    if expected == "array":
        return isinstance(value, list)
    if expected == "string":
        return isinstance(value, str)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "null":
        return value is None
    return True


def validate_contract_value(value, schema, path="$"):
    if not isinstance(schema, dict):
        return
    expected = schema.get("type")
    if isinstance(expected, list):
        if not any(_matches_type(value, item) for item in expected):
            raise ContractValidationError(f"{path}:type")
    elif expected and not _matches_type(value, expected):
        raise ContractValidationError(f"{path}:type")
    if "const" in schema and value != schema["const"]:
        raise ContractValidationError(f"{path}:const")
    if schema.get("enum") is not None and value not in schema["enum"]:
        raise ContractValidationError(f"{path}:enum")
    if isinstance(value, dict):
        required = schema.get("required") or []
        missing = [key for key in required if key not in value]
        if missing:
            raise ContractValidationError(f"{path}:required:{','.join(missing)}")
        if len(value) < int(schema.get("minProperties") or 0):
            raise ContractValidationError(f"{path}:minProperties")
        maximum = schema.get("maxProperties")
        if maximum is not None and len(value) > int(maximum):
            raise ContractValidationError(f"{path}:maxProperties")
        properties = schema.get("properties") or {}
        if schema.get("additionalProperties") is False:
            extras = sorted(set(value) - set(properties))
            if extras:
                raise ContractValidationError(
                    f"{path}:additionalProperties:{','.join(extras)}"
                )
        for key, child in value.items():
            if key in properties:
                validate_contract_value(child, properties[key], f"{path}.{key}")
    if isinstance(value, list):
        if len(value) < int(schema.get("minItems") or 0):
            raise ContractValidationError(f"{path}:minItems")
        maximum = schema.get("maxItems")
        if maximum is not None and len(value) > int(maximum):
            raise ContractValidationError(f"{path}:maxItems")
        for index, child in enumerate(value):
            validate_contract_value(
                child, schema.get("items") or {}, f"{path}[{index}]"
            )
    if isinstance(value, str):
        if len(value) < int(schema.get("minLength") or 0):
            raise ContractValidationError(f"{path}:minLength")
        maximum = schema.get("maxLength")
        if maximum is not None and len(value) > int(maximum):
            raise ContractValidationError(f"{path}:maxLength")
        if schema.get("pattern") and not re.search(schema["pattern"], value):
            raise ContractValidationError(f"{path}:pattern")
        if schema.get("format") == "email" and (
            "@" not in value or value.startswith("@") or value.endswith("@")
        ):
            raise ContractValidationError(f"{path}:email")
        if schema.get("format") == "uuid":
            try:
                uuid.UUID(value)
            except (TypeError, ValueError) as exc:
                raise ContractValidationError(f"{path}:uuid") from exc


def _coerce_parameters(values, schema):
    result = dict(values or {})
    properties = (
        schema.get("properties") or {}
        if isinstance(schema, dict)
        else {}
    )
    for key, value in list(result.items()):
        expected = (properties.get(key) or {}).get("type")
        try:
            if expected == "integer" and isinstance(value, str):
                result[key] = int(value)
            elif expected == "number" and isinstance(value, str):
                result[key] = float(value)
            elif expected == "boolean" and isinstance(value, str):
                lowered = value.lower()
                if lowered in {"true", "1"}:
                    result[key] = True
                elif lowered in {"false", "0"}:
                    result[key] = False
        except ValueError:
            # The validator below produces the stable public error.
            pass
    return result


def invoke_http_contract(
    *,
    function_id,
    contract,
    handler,
    identity,
    path_parameters,
    query_parameters,
    body,
):
    request_schema = contract.get("request_schema") or {}
    query_data = _coerce_parameters(query_parameters, request_schema)
    path_data = _coerce_parameters(path_parameters, request_schema)
    request_data = {}
    request_data.update(query_data)
    if isinstance(body, dict):
        request_data.update(body)
    request_data.update(path_data)
    try:
        validate_contract_value(
            request_data, request_schema
        )
    except ContractValidationError as exc:
        return jsonify({
            "error": "invalid_request",
            "function_id": function_id,
            "detail": str(exc),
        }), 400
    result = handler(
        identity=identity,
        path_parameters=path_data,
        query_parameters=query_data,
        body=dict(body or {}),
    )
    status = 200
    response_body = result
    if isinstance(result, tuple) and len(result) == 2:
        response_body, status = result
    elif isinstance(result, dict) and "body" in result and "status" in result:
        response_body = result["body"]
        status = int(result["status"])
    if 200 <= int(status) < 300:
        try:
            validate_contract_value(
                response_body, contract.get("response_schema") or {}
            )
        except ContractValidationError as exc:
            return jsonify({
                "error": "invalid_backend_response",
                "function_id": function_id,
                "detail": str(exc),
            }), 500
    return jsonify(response_body), int(status)
