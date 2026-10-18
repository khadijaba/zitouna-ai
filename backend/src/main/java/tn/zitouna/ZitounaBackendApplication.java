package tn.zitouna;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.context.properties.ConfigurationPropertiesScan;

@SpringBootApplication
@ConfigurationPropertiesScan
public class ZitounaBackendApplication {

    public static void main(String[] args) {
        SpringApplication.run(ZitounaBackendApplication.class, args);
    }
}
