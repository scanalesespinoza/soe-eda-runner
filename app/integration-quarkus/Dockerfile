FROM eclipse-temurin:21-jre
WORKDIR /work/
COPY target/quarkus-app/lib/ ./lib/
COPY target/quarkus-app/*.jar ./
COPY target/quarkus-app/app/ ./app/
COPY target/quarkus-app/quarkus/ ./quarkus/
EXPOSE 8080
CMD ["java","-jar","quarkus-run.jar"]
