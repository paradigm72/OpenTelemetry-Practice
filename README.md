Tutorial space for learning OTel
https://opentelemetry.io/docs/languages/python/getting-started/
Interested in how to shape metrics and add metadata to understand error patterns and how to shape them to ease issue investigation

Example of what a manually-thrown exception looks like in the collector:
```
SpanEvent #0
      -> Name: exception
      -> Timestamp: 2025-01-02 16:25:18.305219 +0000 UTC
      -> DroppedAttributesCount: 0
      -> Attributes::
           -> exception.type: Str(Exception)
           -> exception.message: Str(Critical fail!)
           -> exception.stacktrace: Str(Exception: Critical fail!)
           -> exception.escaped: Str(False)
```

From code:
```
rollspan.record_exception(Exception("Critical fail!"))
```
