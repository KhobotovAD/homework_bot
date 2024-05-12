class EmptyAPIResponse(Exception):
    """Возвращается пустой словарь ответа API."""

    pass


class HttpStatusNotOK(Exception):
    """Возвращается код, отличный от 200."""

    pass


class RequestError(Exception):
    """Ошибка при запросе к эндпоинту."""

    pass
