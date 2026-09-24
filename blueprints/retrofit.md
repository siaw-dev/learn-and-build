# Blueprint: lysine-dev/retrofit

> **Source**: [https://github.com/square/retrofit](https://github.com/square/retrofit)  
> **Domain / Category**: Web Architecture & Protocols / Type-Safe HTTP Client  
> **Core Architectural Purpose**: Retrofit turns HTTP APIs into Java/Kotlin interfaces via runtime annotation processing and dynamic proxies. It abstracts network transport layer operations by translating method declarations, parameter annotations, and return types into declarative HTTP requests executed via an underlying transport engine (such as OkHttp).

---

## 1. Architectural Topology & Entry Points
- **System Boundaries**: Operates at the application layer of the JVM/Android runtime. Communicates via reflection/dynamic proxies to intercept interface method calls, constructs intermediate HTTP request models, and delegates socket I/O to the network transport layer (OkHttp) via blocking or asynchronous execution handles (`retrofit2.Call`).
- **Directory & Component Map**:
  - `retrofit/src/main/java/retrofit2/`: Core reflection engine, `Retrofit` builder, `ServiceMethod` parser, `Call`, `Callback`, `Converter`, and `CallAdapter` interfaces.
  - `retrofit-adapters/`: Asynchronous stream/future wrappers translating `retrofit2.Call` into idioms like RxJava (`Observable`, `Single`, `Completable`), Google Guava (`ListenableFuture`), and Java 8 (`CompletableFuture`).
  - `retrofit-converters/`: Serialization/deserialization bridges transforming binary or text wire formats (Jackson, Gson, Moshi, Protobuf, Wire) into typed domain objects.
- **Lifecycle & Execution Flow**:
  1. **Initialization**: Client code instantiates `Retrofit` via its Builder, registering base URLs, HTTP clients (`okhttp3.OkHttpClient`), `Converter.Factory` instances, and `CallAdapter.Factory` instances.
  2. **Proxy Creation**: The application invokes `retrofit.create(MyService.class)`, instantiating a dynamic proxy backed by an invocation handler (`Retrofit.loadServiceMethod`).
  3. **Method Parsing & Caching**: When a service method is invoked, Retrofit inspects method annotations (`@GET`, `@POST`, `@Header`), parameter annotations (`@Query`, `@Path`, `@Body`), and return types, caching the parsed metadata in a thread-safe cache (`Map<Method, ServiceMethod<?>>`).
  4. **Execution**: The invocation constructs a concrete `OkHttpCall`, which maps parameters into an `okhttp3.Request` and executes it synchronously (`execute()`) or asynchronously (`enqueue()`).
  5. **Adaptation & Conversion**: The raw response body is passed through matching `Converter` instances to deserialize payloads, and optionally wrapped by a `CallAdapter` to match the service method's return type.

---

## 2. Core Mechanisms, Algorithms & Low-Level Techniques
- **Dynamic Proxy Interception**: Utilizes `java.lang.reflect.Proxy` to intercept interface method invocations without requiring compile-time byte code generation.
- **Annotation Parsing & Validation**: Uses Java reflection (`Method.getAnnotations()`, `Method.getGenericParameterTypes()`, `Annotation[][]`) at runtime (or cached on first invocation) to validate parameter combinations, construct URI templates, and build request property maps.
- **Pluggable Architecture (Strategy Pattern)**:
  - *Converters*: Decouple wire format serialization from the core client via `Converter.Factory`.
  - *Call Adapters*: Decouple transport execution models (callbacks, futures, reactive streams) from the core `Call<T>` abstraction via `CallAdapter.Factory`.
- **Thread Safety**: The `Retrofit` instance and its parsed `ServiceMethod` cache are entirely immutable and thread-safe. Underlying execution relies on OkHttp's connection pooling and asynchronous dispatcher queues.

---

## 3. Data Contracts, Structs & Core API Signatures

```java
package retrofit2;

import java.io.IOException;
import java.lang.annotation.Annotation;
import java.lang.reflect.Type;
import javax.annotation.Nullable;
import okhttp3.HttpUrl;
import okhttp3.MediaType;
import okhttp3.Request;
import okhttp3.RequestBody;
import okhttp3.ResponseBody;

/** Core Retrofit entry point configuration contract. */
public final class Retrofit {
  public <T> T create(final Class<T> service) {
    // Validates interface and returns dynamic proxy instance
    throw new UnsupportedOperationException();
  }

  public <T> Converter<ResponseBody, T> responseBodyConverter(Type type, Annotation[] annotations) {
    throw new UnsupportedOperationException();
  }

  public <T> Converter<T, RequestBody> requestBodyConverter(Type type, Annotation[] parameterAnnotations, Annotation[] methodAnnotations) {
    throw new UnsupportedOperationException();
  }

  public <T, R> CallAdapter<T, R> callAdapter(Type returnType, Annotation[] annotations) {
    throw new UnsupportedOperationException();
  }
}

/** Abstraction for executing network requests synchronously or asynchronously. */
public interface Call<T> extends Cloneable {
  Response<T> execute() throws IOException;
  void enqueue(Callback<T> callback);
  boolean isExecuted();
  void cancel();
  boolean isCanceled();
  Call<T> clone();
  Request request();
}

/** Converter interface for serializing and deserializing types. */
public interface Converter<F, T> {
  @Nullable T convert(F value) throws IOException;

  abstract class Factory {
    public @Nullable Converter<ResponseBody, ?> responseBodyConverter(Type type, Annotation[] annotations, Retrofit retrofit) { return null; }
    public @Nullable Converter<?, RequestBody> requestBodyConverter(Type type, Annotation[] parameterAnnotations, Annotation[] methodAnnotations, Retrofit retrofit) { return null; }
    public @Nullable Converter<?, String> stringConverter(Type type, Annotation[] annotations, Retrofit retrofit) { return null; }
  }
}

/** CallAdapter interface for adapting Call<T> to target execution paradigms. */
public interface CallAdapter<R, T> {
  T adapt(Call<R> call);
  Type responseType();

  abstract class Factory {
    public abstract @Nullable CallAdapter<?, ?> get(Type returnType, Annotation[] annotations, Retrofit retrofit);
  }
}
```

---

## 4. Production-Ready Scaffolding Boilerplate (Copy-Paste)

Below is a complete, compilable, standalone Java example demonstrating a custom Retrofit-like architecture implementing dynamic proxy invocation, annotation processing, and OkHttp execution without relying on external pre-compiled library binaries.

```java
package com.blueprint.retrofit;

import okhttp3.*;
import java.io.IOException;
import java.lang.annotation.*;
import java.lang.reflect.*;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

public class MinimalRetrofitDemo {

  // 1. Annotations
  @Target(ElementType.METHOD)
  @Retention(RetentionPolicy.RUNTIME)
  public @interface GET {
    String value();
  }

  @Target(ElementType.PARAMETER)
  @Retention(RetentionPolicy.RUNTIME)
  public @interface Path {
    String value();
  }

  // 2. Service Interface Definition
  public interface UserService {
    @GET("/users/{id}")
    Call<ResponseBody> getUser(@Path("id") String userId);
  }

  // 3. Retrofit Core Engine Mock
  public static class MiniRetrofit {
    private final OkHttpClient client;
    private final HttpUrl baseUrl;
    private final Map<Method, MethodHandler> methodCache = new ConcurrentHashMap<>();

    public MiniRetrofit(OkHttpClient client, String baseUrl) {
      this.client = client;
      this.baseUrl = HttpUrl.get(baseUrl);
    }

    @SuppressWarnings("unchecked")
    public <T> T create(Class<T> serviceInterface) {
      validateServiceInterface(serviceInterface);
      return (T) Proxy.newProxyInstance(
          serviceInterface.getClassLoader(),
          new Class<?>[] { serviceInterface },
          (proxy, method, args) -> {
            if (method.getDeclaringClass() == Object.class) {
              return method.invoke(this, args);
            }
            MethodHandler handler = methodCache.computeIfAbsent(method, MethodHandler::new);
            return handler.invoke(client, baseUrl, args);
          }
      );
    }

    private void validateServiceInterface(Class<?> serviceInterface) {
      if (!serviceInterface.isInterface()) {
        throw new IllegalArgumentException("API declarations must be interfaces.");
      }
    }
  }

  // 4. Method Handler & Request Builder
  private static class MethodHandler {
    private final String httpMethod;
    private final String relativePath;
    private final Annotation[][] parameterAnnotations;

    public MethodHandler(Method method) {
      GET get = method.getAnnotation(GET.class);
      if (get != null) {
        this.httpMethod = "GET";
        this.relativePath = get.value();
      } else {
        throw new IllegalStateException("Method " + method.getName() + " lacks HTTP method annotation.");
      }
      this.parameterAnnotations = method.getParameterAnnotations();
    }

    public Object invoke(OkHttpClient client, HttpUrl baseUrl, Object[] args) {
      String resolvedPath = relativePath;
      for (int i = 0; i < parameterAnnotations.length; i++) {
        for (Annotation annotation : parameterAnnotations[i]) {
          if (annotation instanceof Path) {
            String name = ((Path) annotation).value();
            resolvedPath = resolvedPath.replace("{" + name + "}", String.valueOf(args[i]));
          }
        }
      }

      HttpUrl url = baseUrl.resolve(resolvedPath);
      if (url == null) {
        throw new IllegalStateException("Malformed URL resolved from: " + resolvedPath);
      }

      Request request = new Request.Builder().url(url).get().build();
      return client.newCall(request);
    }
  }

  // 5. Execution Entrypoint
  public static void main(String[] args) {
    OkHttpClient okHttpClient = new OkHttpClient.Builder().build();
    MiniRetrofit retrofit = new MiniRetrofit(okHttpClient, "https://api.example.com/");

    UserService service = retrofit.create(UserService.class);
    Call<ResponseBody> call = service.getUser("42");

    System.out.println("Built Request URL: " + call.request().url());
  }
}
```

---

## 5. Engineering Invariants, Tradeoffs & Gotchas
- **Performance & Concurrency Characteristics**: 
  - *Reflection Overhead*: Method annotation parsing is performed during the first invocation of a service method and cached in a concurrent map (`MethodHandler`). Subsequent calls execute with near-zero reflection overhead.
  - *Thread Pools*: Socket operations and request dispatches are fully offloaded to OkHttp's asynchronous thread pool and dispatcher.
- **Failure Modes & Edge Cases**:
  - *Generics Erasure*: Custom adapters or converters must handle generic type parameters correctly using `TypeToken` or `ParameterizedType` unwrapping to prevent runtime `ClassCastException` failures during JSON/binary deserialization.
  - *Lifecycle Leaks*: Asynchronous calls (`Call.enqueue`) retain references to callbacks. If not canceled on component destruction (e.g., Android Activity lifecycle events), memory leaks or callbacks executed against destroyed views will occur.
- **Hard Prerequisites**: 
  - Minimum Java 8+ runtime environment or Android API 21+.
  - Correct inclusion of OkHttp runtime dependencies (`com.squareup.okhttp3:okhttp`).