import { TestBed } from '@angular/core/testing';

import { FundingService } from './funding.service';

describe('FundingService', () => {
  let service: FundingService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(FundingService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
