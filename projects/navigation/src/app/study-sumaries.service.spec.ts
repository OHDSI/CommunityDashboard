import { TestBed } from '@angular/core/testing';

import { StudySumariesService } from './study-sumaries.service';

describe('StudySumariesService', () => {
  let service: StudySumariesService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(StudySumariesService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
