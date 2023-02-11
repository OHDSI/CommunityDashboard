import { ComponentFixture, TestBed } from '@angular/core/testing';

import { CommunityDashboardComponent } from './community-dashboard.component';

describe('CommunityDashboardComponent', () => {
  let component: CommunityDashboardComponent;
  let fixture: ComponentFixture<CommunityDashboardComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ CommunityDashboardComponent ]
    })
    .compileComponents();

    fixture = TestBed.createComponent(CommunityDashboardComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
