FROM eclipse-temurin:21-jre
WORKDIR /work/
COPY target/*-runner.jar app.jar
EXPOSE 8080
CMD ["java","-jar","app.jar"]
