import { ComponentFixture, TestBed } from '@angular/core/testing';

import { RepoDrilldownComponent } from './repo-drilldown.component';

describe('RepoDrilldownComponent', () => {
  let component: RepoDrilldownComponent;
  let fixture: ComponentFixture<RepoDrilldownComponent>;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [RepoDrilldownComponent]
    });
    fixture = TestBed.createComponent(RepoDrilldownComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
