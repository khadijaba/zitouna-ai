package tn.zitouna.parcel;

import java.util.List;

import org.springframework.http.HttpStatus;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import tn.zitouna.auth.CurrentUser;

@RestController
@RequestMapping("/api/parcels")
@RequiredArgsConstructor
public class ParcelController {

    private final ParcelService parcelService;

    @GetMapping
    public List<ParcelDto> list(@AuthenticationPrincipal Jwt jwt) {
        return parcelService.list(CurrentUser.id(jwt));
    }

    @GetMapping("/{id}")
    public ParcelDto get(@AuthenticationPrincipal Jwt jwt, @PathVariable Long id) {
        return ParcelDto.from(parcelService.getOwned(CurrentUser.id(jwt), id));
    }

    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    public ParcelDto create(@AuthenticationPrincipal Jwt jwt, @Valid @RequestBody ParcelRequest request) {
        return parcelService.create(CurrentUser.id(jwt), request);
    }

    @PutMapping("/{id}")
    public ParcelDto update(@AuthenticationPrincipal Jwt jwt, @PathVariable Long id,
            @Valid @RequestBody ParcelRequest request) {
        return parcelService.update(CurrentUser.id(jwt), id, request);
    }

    @DeleteMapping("/{id}")
    @ResponseStatus(HttpStatus.NO_CONTENT)
    public void delete(@AuthenticationPrincipal Jwt jwt, @PathVariable Long id) {
        parcelService.delete(CurrentUser.id(jwt), id);
    }
}
