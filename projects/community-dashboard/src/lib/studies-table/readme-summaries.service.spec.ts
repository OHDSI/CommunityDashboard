import { HttpClientTestingModule } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';

import { ReadmeSummariesService } from './readme-summaries.service';

describe('ReadmeSummariesService', () => {
  let service: ReadmeSummariesService;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [
        HttpClientTestingModule,
      ]
    });
    service = TestBed.inject(ReadmeSummariesService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
