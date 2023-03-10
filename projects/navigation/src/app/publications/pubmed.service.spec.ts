import { TestBed } from '@angular/core/testing';

import { PubmedService } from './pubmed.service';

describe('PubmedService', () => {
  let service: PubmedService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(PubmedService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
