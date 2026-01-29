# Stage 1: Build stage
# We use the full JDK to compile the code
FROM eclipse-temurin:17-jdk-jammy AS build
WORKDIR /app

# 1. Copy the Gradle executable files first
# This includes the wrapper and the configuration
COPY gradlew .
COPY gradle ./gradle
COPY build.gradle settings.gradle ./

# 2. Fix permissions (crucial for Mac/Linux compatibility)
RUN chmod +x gradlew

# 3. Download dependencies
# This is a separate step so Docker caches your libraries.
# It won't re-download them unless you change build.gradle.
RUN ./gradlew dependencies --no-daemon

# 4. Copy the source code and build the executable JAR
COPY src ./src
RUN ./gradlew bootJar -x test --no-daemon

# Stage 2: Runtime stage
# We switch to a much smaller JRE image for the final container
FROM eclipse-temurin:17-jre-jammy
WORKDIR /app

# 5. Create a dedicated user to run the app (Security Best Practice)
RUN useradd -m spring
USER spring

# 6. Copy the built JAR from the first stage
# We use a wildcard *.jar to ensure we grab the generated file
COPY --from=build /app/build/libs/*.jar app.jar

# 7. Expose the port your Spring app runs on
EXPOSE 8080

# 8. Run the application
ENTRYPOINT ["java", "-jar", "app.jar"]
