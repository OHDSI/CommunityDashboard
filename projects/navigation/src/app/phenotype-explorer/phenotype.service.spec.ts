import { TestBed } from '@angular/core/testing';

import { PhenotypeService } from './phenotype.service';

describe('PhenotypeService', () => {
  let service: PhenotypeService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(PhenotypeService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
