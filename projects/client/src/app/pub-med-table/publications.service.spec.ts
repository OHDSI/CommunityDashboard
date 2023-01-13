import { HttpClientTestingModule } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';

import { PublicationsService } from './publications.service';

describe('PubMedService', () => {
  let service: PublicationsService;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [
        HttpClientTestingModule,
      ]
    });
    service = TestBed.inject(PublicationsService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
