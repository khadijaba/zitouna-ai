package tn.zitouna.admin;

import static org.assertj.core.api.Assertions.assertThat;
import static org.hamcrest.Matchers.greaterThanOrEqualTo;
import static org.hamcrest.Matchers.hasItem;
import static org.hamcrest.Matchers.hasSize;
import static org.springframework.security.test.web.servlet.setup.SecurityMockMvcConfigurers.springSecurity;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.delete;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.patch;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.context.TestPropertySource;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;
import org.springframework.web.context.WebApplicationContext;

import com.jayway.jsonpath.JsonPath;

import tn.zitouna.user.Role;
import tn.zitouna.user.User;
import tn.zitouna.user.UserRepository;

/** Back-office API through the real security chain. The admin comes from app.admin.* (AdminBootstrap). */
@SpringBootTest
@ActiveProfiles("test")
@TestPropertySource(properties = { "app.admin.email=admin@test.tn", "app.admin.password=admin-pass-123" })
class AdminControllerTest {

    @Autowired
    private WebApplicationContext context;

    @Autowired
    private UserRepository users;

    @Autowired
    private AdminBootstrap bootstrap;

    private MockMvc mvc;

    @BeforeEach
    void setUp() {
        mvc = MockMvcBuilders.webAppContextSetup(context).apply(springSecurity()).build();
    }

    private String login(String email, String password) throws Exception {
        String body = mvc.perform(post("/api/auth/login").contentType(MediaType.APPLICATION_JSON)
                .content("{\"email\":\"" + email + "\",\"password\":\"" + password + "\"}"))
                .andExpect(status().isOk()).andReturn().getResponse().getContentAsString();
        return "Bearer " + JsonPath.read(body, "$.token");
    }

    /** Registers a farmer and returns [bearer, user id]. */
    private Object[] farmer(String email) throws Exception {
        String body = mvc.perform(post("/api/auth/register").contentType(MediaType.APPLICATION_JSON)
                .content("{\"fullName\":\"Farmer " + email + "\",\"email\":\"" + email + "\",\"password\":\"zitouna123\"}"))
                .andExpect(status().isCreated()).andReturn().getResponse().getContentAsString();
        return new Object[] { "Bearer " + JsonPath.read(body, "$.token"), ((Number) JsonPath.read(body, "$.user.id")).longValue() };
    }

    @Test
    void farmersAndAnonymousAreRefused() throws Exception {
        String bearer = (String) farmer("adm-refused@example.tn")[0];
        mvc.perform(get("/api/admin/stats")).andExpect(status().isUnauthorized());
        mvc.perform(get("/api/admin/stats").header("Authorization", bearer))
                .andExpect(status().isForbidden())
                .andExpect(jsonPath("$.detail").value("Réservé aux administrateurs"));
        mvc.perform(get("/api/admin/users").header("Authorization", bearer)).andExpect(status().isForbidden());
    }

    @Test
    void adminSeesStatsUsersParcelsAndPredictions() throws Exception {
        String admin = login("admin@test.tn", "admin-pass-123");
        Object[] f = farmer("adm-salah@example.tn");
        mvc.perform(post("/api/parcels").header("Authorization", f[0]).contentType(MediaType.APPLICATION_JSON)
                .content("""
                        {"name":"Henchir Sfax","governorate":"Sfax","latitude":34.74,"longitude":10.76,
                         "areaHa":2.5,"treeCount":250,"irrigated":true}"""))
                .andExpect(status().isCreated());

        mvc.perform(get("/api/admin/stats").header("Authorization", admin))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.users").value(greaterThanOrEqualTo(2)))
                .andExpect(jsonPath("$.admins").value(greaterThanOrEqualTo(1)))
                .andExpect(jsonPath("$.trees").value(greaterThanOrEqualTo(250)))
                .andExpect(jsonPath("$.last30Days", hasSize(30)))
                .andExpect(jsonPath("$.predictionsByType.DISEASE").value(0))
                .andExpect(jsonPath("$.status.modules", hasSize(6)));

        mvc.perform(get("/api/admin/users").param("q", "adm-salah").header("Authorization", admin))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.content[0].email").value("adm-salah@example.tn"))
                .andExpect(jsonPath("$.content[0].parcels").value(1))
                .andExpect(jsonPath("$.content[0].role").value("FARMER"));

        mvc.perform(get("/api/admin/parcels").header("Authorization", admin))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.content[*].ownerEmail", hasItem("adm-salah@example.tn")));

        mvc.perform(get("/api/admin/predictions").param("type", "DISEASE").header("Authorization", admin))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.totalElements").value(0));
    }

    @Test
    void adminDeletesUsersAndParcelsButRolesCannotChange() throws Exception {
        String admin = login("admin@test.tn", "admin-pass-123");
        Object[] f = farmer("adm-karim@example.tn");
        long farmerId = (Long) f[1];

        // Exactly one admin, from .env: no endpoint to promote anybody.
        mvc.perform(patch("/api/admin/users/" + farmerId + "/role").header("Authorization", admin)
                .contentType(MediaType.APPLICATION_JSON).content("{\"role\":\"ADMIN\"}"))
                .andExpect(status().is4xxClientError());
        mvc.perform(get("/api/users/me").header("Authorization", (String) f[0]))
                .andExpect(jsonPath("$.role").value("FARMER"));

        String me = mvc.perform(get("/api/users/me").header("Authorization", admin))
                .andReturn().getResponse().getContentAsString();
        long adminId = ((Number) JsonPath.read(me, "$.id")).longValue();
        mvc.perform(delete("/api/admin/users/" + adminId).header("Authorization", admin))
                .andExpect(status().isConflict())
                .andExpect(jsonPath("$.detail").value("Le compte administrateur ne peut pas être supprimé"));

        String parcel = mvc.perform(post("/api/parcels").header("Authorization", f[0])
                .contentType(MediaType.APPLICATION_JSON)
                .content("""
                        {"name":"Zitouna","governorate":"Sousse","latitude":35.8,"longitude":10.6,"irrigated":false}"""))
                .andReturn().getResponse().getContentAsString();
        Integer parcelId = JsonPath.read(parcel, "$.id");
        mvc.perform(delete("/api/admin/parcels/" + parcelId).header("Authorization", admin))
                .andExpect(status().isNoContent());
        mvc.perform(get("/api/parcels/" + parcelId).header("Authorization", f[0]))
                .andExpect(status().isNotFound());

        mvc.perform(delete("/api/admin/users/" + farmerId).header("Authorization", admin))
                .andExpect(status().isNoContent());
        mvc.perform(delete("/api/admin/users/" + farmerId).header("Authorization", admin))
                .andExpect(status().isNotFound());
    }

    @Test
    void startUpKeepsExactlyOneAdmin() throws Exception {
        // Another account that became ADMIN somehow (old data, manual SQL...).
        User intruder = users.findById((Long) farmer("adm-intruder@example.tn")[1]).orElseThrow();
        intruder.setRole(Role.ADMIN);
        users.save(intruder);

        bootstrap.run(null);

        assertThat(users.findByRole(Role.ADMIN)).extracting(User::getEmail).containsExactly("admin@test.tn");
        assertThat(users.findByEmailIgnoreCase("adm-intruder@example.tn").orElseThrow().getRole()).isEqualTo(Role.FARMER);
        login("admin@test.tn", "admin-pass-123"); // the .env password still works
    }
}
