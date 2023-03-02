import { HttpClientTestingModule } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';

import { YouTubeService } from './you-tube.service';

describe('YouTubeService', () => {
  let service: YouTubeService;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [
        HttpClientTestingModule,
      ]
    });
    service = TestBed.inject(YouTubeService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
